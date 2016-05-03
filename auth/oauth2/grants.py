# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""
Implementations for the client credentials & JWT-bearer authorization grants
"""
import couch
from tornado.gen import coroutine, Return
from tornado.options import options
from perch import Repository, Service

from .scope import Scope
from .token import generate_token, decode_token
from .exceptions import InvalidGrantType, BadRequest, Unauthorized

_registry = {}


def get_grant(request, token=None):
    """Grant factory"""
    if token is None:
        key = request.grant_type
    else:
        decoded = decode_token(token)
        key = decoded['grant_type']

    try:
        grant_type = _registry[key]
    except KeyError:
        raise InvalidGrantType(key)

    return grant_type(request)


class BaseGrant(object):
    def __init__(self, request):
        self.request = request

    @classmethod
    def register(cls):
        """Register the class in the registry"""
        _registry[cls.grant_type] = cls

    def validate_grant(self):
        """Validate the grant is supported"""
        if self.request.grant_type != self.grant_type:
            raise InvalidGrantType(self.request.grant_type)

    @property
    def requested_scope(self):
        """
        The requested scope when generating a token.

        Defaults to `default_scope` if not provided
        """
        scope = getattr(self, '_scope', None)
        if not scope:
            try:
                scope = self.request.body_arguments['scope'][0]
            except (KeyError, IndexError):
                scope = options.default_scope

            self._scope = scope = Scope(scope)

        return scope

    @property
    def requested_access(self):
        """The access a client has requested from a service"""
        access = getattr(self, '_access', None)
        if not access:
            try:
                access = self.request.body_arguments['requested_access'][0]
            except (KeyError, IndexError):
                access = None

            if not access:
                raise BadRequest('Missing requested_access argument')

            self._access = access

        return access

    @property
    def hosted_resource(self):
        """
        Is the protected resource hosted by another service

        For example a repository is hosted in a repository service
        """
        try:
            resource_id = self.request.body_arguments['resource_id'][0]
        except (KeyError, IndexError):
            return None

        # During this request the client is the service making a request to
        # verify access to the resource. The resource is not hosted by the
        # service if the service and resource ID are the same
        if self.request.client_id == resource_id:
            resource_id = None

        return resource_id

    @coroutine
    def generate_token(self):
        raise NotImplementedError()

    def verify_scope(self, scope):
        """Verify the requested access is permitted by the token's scope"""
        if self.hosted_resource:
            resource_id = self.hosted_resource
            within_scope = self._verify_hosted_resource_within_scope(scope)
        else:
            resource_id = self.request.client_id
            within_scope = self._verify_resource_within_scope(scope)

        if not within_scope:
            raise Unauthorized("'{}' access to '{}' not permitted by token"
                               .format(self.requested_access, resource_id))

    def _verify_hosted_resource_within_scope(self, scope):
        """Verify access to a hosted resource is within scope"""
        return scope.within_scope(self.requested_access,
                                  self.hosted_resource)

    def _verify_resource_within_scope(self, scope):
        """
        Verify access to a resource is within scope

        Checks the client ID & URL
        """
        id_in_scope = scope.within_scope(self.requested_access,
                                         self.request.client_id)
        try:
            url_in_scope = scope.within_scope(self.requested_access,
                                              self.request.client.location)
        except AttributeError:
            url_in_scope = False

        return id_in_scope or url_in_scope

    @coroutine
    def verify_access_hosted_resource(self, client):
        """
        Verify access to a resource hosted on a service

        It's assumed the hosted resource is a repository
        """
        if not self.hosted_resource:
            raise Return(True)

        try:
            repo = yield Repository.get(self.hosted_resource)
        except couch.NotFound:
            raise Unauthorized("Unknown repository '{}'"
                               .format(self.hosted_resource))

        if self.request.client_id != repo.service_id:
            raise Unauthorized("'{}' does not host repository '{}'"
                               .format(self.request.client_id,
                                       self.hosted_resource))

        has_access = client.authorized(self.requested_access, repo)
        if not has_access:
            raise Unauthorized(
                "'{}' does not have '{}' access to repository '{}'"
                .format(client.id, self.requested_access,
                        self.hosted_resource))

        raise Return(True)

    @coroutine
    def verify_access_service(self, client):
        """
        Verify the token's client / delegate has access to the service
        """
        try:
            service = yield Service.get(self.request.client_id)
        except couch.NotFound:
            raise Unauthorized("Unknown service '{}'"
                               .format(self.request.client_id))
        has_access = client.authorized(self.requested_access, service)

        if not has_access:
            raise Unauthorized("'{}' does not have '{}' to service '{}'"
                               .format(client.id, self.requested_access,
                                       self.request.client_id))

        raise Return(True)

    @coroutine
    def verify_access(self, token):
        raise NotImplementedError()


class ClientCredentials(BaseGrant):
    """
    Implementation of the OAuth2 client credentials grant

    See https://tools.ietf.org/html/rfc6749
    """
    grant_type = 'client_credentials'

    @coroutine
    def validate_scope(self):
        """Vaildate that the client is authorized for the requested scope"""
        yield self.requested_scope.validate(self.request.client)

    @coroutine
    def generate_token(self):
        """Verify the client is authorized and generate a token"""
        self.validate_grant()
        yield self.validate_scope()
        token, expiry = generate_token(self.request.client,
                                       self.requested_scope,
                                       self.grant_type)

        raise Return((token, expiry))

    @coroutine
    def verify_access(self, token):
        """Verify a token has access to a resource"""
        decoded = decode_token(token)
        scope = decoded['scope']
        client = yield Service.get(decoded['client']['id'])

        self.verify_scope(scope)
        yield [self.verify_access_service(client),
               self.verify_access_hosted_resource(client)]


ClientCredentials.register()


class AuthorizeDelegate(BaseGrant):
    """
    Use the JWT Bearer authorization grant for authorizing a delegate

    See https://tools.ietf.org/html/rfc7523
    """
    grant_type = 'urn:ietf:params:oauth:grant-type:jwt-bearer'

    @property
    def assertion(self):
        """
        The assertion should be a JSON Web Token authorizing the client
        to request a token to act as a delegate on another client's behalf
        """
        assertion = getattr(self, '_assertion', None)

        if not assertion:
            try:
                assertion = self.request.body_arguments['assertion'][0]
            except (KeyError, IndexError):
                raise ValueError('A JSON Web Token must be included as an '
                                 '"assertion" parameter')

            self._assertion = assertion = decode_token(assertion)

        return assertion

    def validate_scope(self):
        """Vaildate that the client's scope is granted by the provided JWT"""
        id_scope = 'delegate[{}]:{}'.format(
            self.request.client_id,
            str(self.requested_scope))
        try:
            url_scope = 'delegate[{}]:{}'.format(
                self.request.client.location,
                str(self.requested_scope))
        except AttributeError:
            url_scope = None

        if str(self.assertion['scope']) not in (id_scope, url_scope):
            raise Unauthorized('Requested scope does not match token')

    @coroutine
    def generate_token(self):
        """Generate a delegate token"""
        self.validate_grant()
        self.validate_scope()

        # Assuming delegation always requires write access
        # should change it to a param
        client = yield Service.get(self.assertion['client']['id'])
        has_access = client.authorized('w', self.request.client)

        if not has_access:
            raise Unauthorized('Client "{}" may not delegate to service "{}"'.format(
                self.assertion['client']['id'],
                self.request.client_id
            ))

        token, expiry = generate_token(client,
                                       self.requested_scope,
                                       self.grant_type,
                                       delegate_id=self.request.client_id)

        raise Return((token, expiry))

    @coroutine
    def verify_access(self, token):
        """Verify a token has access to a resource"""
        decoded = decode_token(token)
        scope = decoded['scope']

        self.verify_scope(scope)

        try:
            delegate = yield Service.get(decoded['sub'])
        except couch.NotFound:
            raise Unauthorized("Unknown delegate '{}'".format(decoded['sub']))

        client = yield Service.get(decoded['client']['id'])

        yield [self.verify_access_service(delegate),
               self.verify_access_service(client),
               self.verify_access_hosted_resource(client)]


AuthorizeDelegate.register()
