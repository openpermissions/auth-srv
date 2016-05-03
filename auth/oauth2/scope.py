# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""
Scopes
------

The following scopes are available:

    - read
    - write
    - delegate

The "read" scope permits the client to read a protected resource.
This is the default scope.

The "write" scope permits a client to write to a protected resource.
Unilke "read", "write" must also include the identity of the
resource, within "[]" brackets, e.g. "write[1234]" allows writing to a
resource identified by 1234. Services may also be identied with it's registered
URL, e.g. "write[http://test.com]". The auth service verifies whether the
client is permitted to write to the resource before issuing an access
token.

The "delegate" scope is used to delegate writing to a resource, e.g.
the onboarding service accesses the repository on the client's behalf
To access the resource, the delegate will exchange the token for a new
"write" token.

The delegate scope has the form

    delegate[<service id or url>]:write[<resource id or url>]

Where service id or url is the delegate service's ID or URL (e.g. the
onbooarding service URL), and the resource id or URL is the protected
resource's ID or URL (e.g. the repository ID).

The advantage of using "delegate" instead of "write" is that the token can
only be used by the specified delegate (assuming the delegate keeps their
credentials secure), and the delegate will only be able to write to the
specified resource.
"""
import re
from collections import defaultdict, namedtuple
from functools import partial

import couch
from perch import views, Repository, Service
from tornado.gen import coroutine, Return

from .exceptions import InvalidScope, Unauthorized

READ = 'read'
READ_REGEX = re.compile(r'^read\[(?P<resource_id>.+)\]$')
WRITE = 'write'
WRITE_REGEX = re.compile(r'^write\[(?P<resource_id>.+)\]$')
DELEGATE = 'delegate'
DELEGATE_REGEX = re.compile(r'^delegate\[(?P<delegate_id>.+)\]:(?P<delegated_action>read|write)\[(?P<resource_id>.+)\]$')
ACCESS_MAPPING = {
    READ: 'r',
    WRITE: 'w'
}
RESOURCE_TYPES = {
    Repository.resource_type: Repository,
    Service.resource_type: Service,
}


Access = namedtuple('Access', ['access', 'delegate_id'])


class Scope(object):
    def __init__(self, scope):
        self.scope = scope
        # read is True if the scope is for reading any resource
        self.read = False
        try:
            self._group()
        except KeyError:
            raise InvalidScope('Invalid action')

    def __str__(self):
        return self.scope

    def __repr__(self):
        return '<Scope: {}>'.format(self.scope)

    def _group(self):
        """
        Group scope string by actions and resources

        Raises InvalidScope the scope is invalid
        """
        self.resources = defaultdict(set)
        self.delegates = defaultdict(set)

        for x in self.scope.split():
            if x.startswith(READ):
                self._add_read(x)
            elif x.startswith(WRITE):
                self._add_write(x)
            elif x.startswith(DELEGATE):
                self._add_delegate(x)
            else:
                raise InvalidScope('Scope has missing elements')

    def _add_read(self, scope):
        """Add 'read' scope to self.resources"""
        access = ACCESS_MAPPING[READ]
        matched = re.match(READ_REGEX, scope)

        if not matched:
            self.read = True
        else:
            resource_id = matched.group('resource_id')
            self.resources[resource_id].add(Access(access, None))

    def _add_write(self, scope):
        """Add 'write' scope to self.resources"""
        access = ACCESS_MAPPING[WRITE]
        matched = re.match(WRITE_REGEX, scope)

        if not matched:
            raise InvalidScope('Write scope requires a resource ID')

        resource_id = matched.group('resource_id')
        self.resources[resource_id].add(Access(access, None))

    def _add_delegate(self, scope):
        """Add 'delegate' scope to self.delegates & self.resources"""
        matched = re.match(DELEGATE_REGEX, scope)

        if not matched:
            raise InvalidScope('Invalid delegate scope')

        resource_id = matched.group('resource_id')
        delegate_id = matched.group('delegate_id')
        access = ACCESS_MAPPING[matched.group('delegated_action')]

        self.delegates[delegate_id].add(Access(access, None))
        self.resources[resource_id].add(Access(access, delegate_id))

    def within_scope(self, access, resource_id):
        """Is accessing the resource within this scope"""
        if access in ('r', 'rw') and self.read is True:
            return True

        access_set = {Access(x, None) for x in access if x in 'rw'}

        return bool(access_set & (self.resources[resource_id] | self.delegates[resource_id]))

    @coroutine
    def validate(self, client):
        """
        Validate the requested OAuth2 scope

        If a "write" or "delegate" scope is requested then also checks access
        to the resource and delegate

        :param scope: tornado.httputil.HTTPServerRequest
        :param client: the client object. Used to check the client is
            authorized for the requested scope
        :param default_scope: the default scope if not included in the request
        :raise:
            InvalidScope: The scope is invalid
            Unauthorized: The client is not authorized for the scope
        """
        resource_func = partial(self._check_access_resource, client)
        delegate_func = partial(self._check_access_delegate, client)

        yield [self._check_access_resources(resource_func, self.resources),
               self._check_access_resources(delegate_func, self.delegates)]

    @coroutine
    def _check_access_resources(self, func, resources):
        """Check resources exist and then call func for each resource"""
        grouped = {'ids': {}, 'urls': {}}

        for k, v in resources.items():
            if k.startswith('http'):
                grouped['urls'][k] = v
            else:
                grouped['ids'][k] = v

        yield [self._check_access_resource_ids(func, grouped['ids']),
               self._check_access_resource_urls(func, grouped['urls'])]

    @coroutine
    def _check_access_resource_ids(self, func, resources):
        """
        Check resource identified by an ID exist and then call func for
        each resource
        """
        if not resources:
            raise Return()

        for resource_id in resources:
            try:
                doc = yield views.service_and_repository.first(key=resource_id)
            except couch.NotFound:
                raise InvalidScope('Scope contains an unknown resource ID')

            resource = RESOURCE_TYPES[doc['value']['type']](**doc['value'])
            try:
                yield resource.get_parent()
            except couch.NotFound:
                raise InvalidScope('Invalid resource - missing parent')
            func(resource, resources[resource_id])

    @coroutine
    def _check_access_resource_urls(self, func, resources):
        """
        Check resource identified by an URL exist and then call func for each
        resource
        """
        for url in resources:
            try:
                resource = yield Service.get_by_location(url)
            except couch.NotFound:
                raise InvalidScope("Scope contains an unknown location: '{}'"
                                   .format(url))

            func(resource, resources[url])

    def _concatenate_access(self, access):
        """Concatenate a resource's access"""
        return ''.join(sorted(list({x.access for x in access})))

    def _check_access_resource(self, client, resource, access):
        """Check the client has access to the resource"""
        requested_access = self._concatenate_access(access)
        has_access = client.authorized(requested_access, resource)

        if not has_access:
            raise Unauthorized(
                "Client '{}' does not have '{}' access to '{}'"
                .format(client.id, requested_access, resource.id))

    def _check_access_delegate(self, client, delegate, access):
        """Check delegate is the correct type and check access"""
        if delegate.type != Service.resource_type:
            raise InvalidScope("Only services can be delegates. '{}' is a '{}'"
                               .format(delegate.id, delegate.type))

        self._check_access_resource(client, delegate, access)
