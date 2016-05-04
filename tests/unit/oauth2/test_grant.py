# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import jwt
import pytest
from koi.test_helpers import make_future
from mock import call, patch
import perch
from perch import exceptions
from tornado.testing import AsyncTestCase, gen_test
from tornado.gen import coroutine

from auth.oauth2 import grants, Scope
from auth.oauth2.token import decode_token, generate_token


ORGANISATION = perch.Organisation(id='org1', state=perch.State.approved)


class FakeRequest(object):
    def __init__(self, client_id='client_id', client=None, scope='read',
                 grant_type='fake grant', **kwargs):
        if client is None:
            self.client_id = client_id
            self.client = perch.Service(
                parent=ORGANISATION,
                organisation_id=ORGANISATION.id,
                id=client_id,
                location='http://test.client',
                state=perch.State.approved
            )
        else:
            self.client_id = client.id
            self.client = client
        self.grant_type = grant_type
        self.body_arguments = {
            'scope': [scope]
        }
        self.body_arguments.update(kwargs)


class TestBaseGrant(AsyncTestCase):
    def setUp(self):
        super(TestBaseGrant, self).setUp()
        self.scope = 'read'
        self.request = FakeRequest()

        class Grant(grants.BaseGrant):
            grant_type = self.request.grant_type

        self.Grant = Grant

    def test_register_grant(self):
        self.Grant.register()

        instance = grants.get_grant(self.request)
        assert isinstance(instance, self.Grant)

    def test_unregistered_grant(self):
        with pytest.raises(grants.InvalidGrantType):
            grants.get_grant(FakeRequest(grant_type='unregistered grant'))

    def test_get_grant_with_token(self):
        client = perch.Service(
            id='test',
            service_type='service_type',
            organisation_id='organisation_id'
        )
        token, expiry = generate_token(client, self.scope,
                                       self.Grant.grant_type)
        request = FakeRequest(grant_type=None)
        self.Grant.register()

        instance = grants.get_grant(request, token)

        assert isinstance(instance, self.Grant)

    def test_valid_grant(self):
        self.Grant(self.request).validate_grant()

    def test_invalid_grant(self):
        self.Grant.grant_type = 'something else'

        with pytest.raises(grants.InvalidGrantType):
            self.Grant(self.request).validate_grant()

    def test_requested_scope(self):
        grant = self.Grant(self.request)

        assert str(grant.requested_scope) == self.scope

    def test_hosted_resource(self):
        self.request.body_arguments['resource_id'] = ['something']
        grant = self.Grant(self.request)

        assert grant.hosted_resource == 'something'

    def test_no_resource_id(self):
        grant = self.Grant(self.request)

        assert grant.hosted_resource is None

    def test_resource_id_same_as_client_id(self):
        self.request.body_arguments['resource_id'] = [self.request.client_id]
        grant = self.Grant(self.request)

        assert grant.hosted_resource is None

    def test_multiple_resource_ids(self):
        self.request.body_arguments['resource_id'] = ['a', 'b']
        grant = self.Grant(self.request)

        assert grant.hosted_resource == 'a'

    def test_verify_scope(self):
        self.request.body_arguments['requested_access'] = ['r']
        scope = Scope('read')
        grant = self.Grant(self.request)

        grant.verify_scope(scope)

    def test_verify_scope_url(self):
        self.request.body_arguments['requested_access'] = ['r']
        scope = Scope('read[http://test.client]')
        grant = self.Grant(self.request)

        grant.verify_scope(scope)

    def test_verify_scope_specified_resource(self):
        self.request.body_arguments['requested_access'] = ['r']
        scope = Scope('read:{}'.format(self.request.client_id))
        grant = self.Grant(self.request)

        grant.verify_scope(scope)

    def test_verify_scope_hosted_resource(self):
        self.request.body_arguments['requested_access'] = ['r']
        self.request.body_arguments['resource_id'] = ['1234']
        scope = Scope('read:1234')
        grant = self.Grant(self.request)

        grant.verify_scope(scope)

    def test_scope_mismatch(self):
        self.request.body_arguments['requested_access'] = ['r']
        scope = Scope('write[{}]'.format(self.request.client_id))
        grant = self.Grant(self.request)

        with pytest.raises(grants.Unauthorized):
            grant.verify_scope(scope)

    def test_scope_mismatch_hosted_resource(self):
        self.request.body_arguments['requested_access'] = ['r']
        self.request.body_arguments['resource_id'] = ['1234']
        scope = Scope('write[1234]')
        grant = self.Grant(self.request)

        with pytest.raises(grants.Unauthorized):
            grant.verify_scope(scope)

    def test_verify_scope_different_url(self):
        self.request.body_arguments['requested_access'] = ['r']
        scope = Scope('read[http://other.client]')
        grant = self.Grant(self.request)

        with pytest.raises(grants.Unauthorized):
            grant.verify_scope(scope)

    @gen_test
    def test_verify_access_no_hosted_resource(self):
        grant = self.Grant(self.request)

        result = yield grant.verify_access_hosted_resource({})

        assert result is True

    @gen_test
    def test_verify_access_hosted_resource(self):
        self.request.body_arguments['requested_access'] = ['r']
        self.request.body_arguments['resource_id'] = ['1234']

        with patch.object(grants.Repository, 'get') as repo_get:
            client = perch.Service(
                parent=ORGANISATION,
                id='something',
                organisation_id=ORGANISATION.id,
                service_type='external',
                state=perch.State.approved,
            )
            repo = perch.Repository(
                parent=ORGANISATION,
                organisation_id=ORGANISATION.id,
                service_id=self.request.client_id,
                state=perch.State.approved,
                permissions=[
                    {'type': 'organisation_id',
                     'value': ORGANISATION.id,
                     'permission': 'rw'
                     }
                ]
            )
            repo_get.return_value = make_future(repo)

            grant = self.Grant(self.request)
            result = yield grant.verify_access_hosted_resource(client)

        assert result is True

    @gen_test
    def test_verify_access_hosted_resource_does_not_exist(self):
        self.request.body_arguments['resource_id'] = ['1234']

        with patch.object(grants.Repository, 'get') as repo_get:
            repo_get.side_effect = exceptions.NotFound()

            grant = self.Grant(self.request)
            with pytest.raises(grants.Unauthorized):
                yield grant.verify_access_hosted_resource({})

    @gen_test
    def test_verify_access_hosted_resource_service_mismatch(self):
        self.request.body_arguments['resource_id'] = ['1234']
        with patch.object(grants.Repository, 'get') as repo_get:
            client = perch.Service(
                parent=ORGANISATION,
                id='something',
                organisation_id=ORGANISATION.id,
                service_type='external',
                state=perch.State.approved,
            )
            repo = perch.Repository(
                parent=ORGANISATION,
                organisation_id=ORGANISATION.id,
                service_id='something else',
                state=perch.State.approved,
                permissions=[
                    {'type': 'organisation_id',
                     'value': ORGANISATION.id,
                     'permission': 'rw'
                     }
                ]
            )
            repo_get.return_value = make_future(repo)

            grant = self.Grant(self.request)
            with pytest.raises(grants.Unauthorized):
                yield grant.verify_access_hosted_resource(client)

    @gen_test
    def test_cannot_access_hosted_resource(self):
        self.request.body_arguments['requested_access'] = ['r']
        self.request.body_arguments['resource_id'] = ['1234']
        with patch.object(grants.Repository, 'get') as repo_get:
            client = perch.Service(
                parent=ORGANISATION,
                id='something',
                organisation_id=ORGANISATION.id,
                service_type='external',
                state=perch.State.approved
            )
            repo = perch.Repository(
                parent=ORGANISATION,
                service_id=self.request.client.id,
                organisation_id=ORGANISATION.id,
                state=perch.State.approved,
                permissions=[
                    {'type': 'organisation_id',
                     'value': client.organisation_id,
                     'permission': '-'
                     }
                ]
            )
            repo_get.return_value = make_future(repo)

            grant = self.Grant(self.request)
            with pytest.raises(grants.Unauthorized):
                yield grant.verify_access_hosted_resource(client)

    @gen_test
    def test_verify_access_service(self):
        self.request.body_arguments['requested_access'] = ['r']
        with patch.object(grants.Service, 'get') as service_get:
            client = perch.Service(
                parent=ORGANISATION,
                id='something',
                organisation_id=ORGANISATION.id,
                service_type='external',
                state=perch.State.approved
            )
            service = perch.Repository(
                parent=ORGANISATION,
                organisation_id=ORGANISATION.id,
                state=perch.State.approved,
                permissions=[
                    {'type': 'organisation_id',
                     'value': client.organisation_id,
                     'permission': 'rw'
                     }
                ]
            )
            service_get.return_value = make_future(service)

            grant = self.Grant(self.request)
            yield grant.verify_access_service(client)

    @gen_test
    def test_verify_access_service_does_not_have_access(self):
        self.request.body_arguments['requested_access'] = ['r']
        with patch.object(grants.Service, 'get') as service_get:
            client = perch.Service(
                parent=ORGANISATION,
                id='something',
                organisation_id=ORGANISATION.id,
                service_type='external'
            )
            service = perch.Repository(
                parent=ORGANISATION,
                organisation_id=ORGANISATION.id,
                permissions=[
                    {'type': 'organisation_id',
                     'value': client.organisation_id,
                     'permission': '-'
                     }
                ]
            )
            service_get.return_value = make_future(service)

            grant = self.Grant(self.request)
            with pytest.raises(grants.Unauthorized):
                yield grant.verify_access_service(client)


class TestClientCredentialsGrant(AsyncTestCase):
    def setUp(self):
        super(TestClientCredentialsGrant, self).setUp()

        self.scope = 'read'
        self.client = perch.Service(
            id='a client id',
            organisation_id='an organisation id',
            service_type='external'
        )
        self.request = FakeRequest(
            grant_type=grants.ClientCredentials.grant_type,
            scope=self.scope,
            client=self.client)

    @patch('auth.oauth2.grants.generate_token')
    @gen_test
    def test_generate_token(self, generate_token):
        generate_token.return_value = ('token', 'expiry')
        grant = grants.ClientCredentials(self.request)

        with patch.object(grant.requested_scope, 'validate') as validate_scope:
            validate_scope.return_value = make_future(None)
            token, expiry = yield grant.generate_token()

        assert token, expiry == generate_token()
        validate_scope.assert_called_once_with(self.request.client)

    @patch.object(grants.ClientCredentials, 'verify_access_service',
                  return_value=make_future(True))
    @patch.object(grants.ClientCredentials, 'verify_access_hosted_resource',
                  return_value=make_future(True))
    @gen_test
    def test_verify_access1(self, resource, service):
        protected_service = perch.Service(
            id='1234',
            location='http://test.client'
        )
        token, expiry = generate_token(
            self.client,
            self.scope,
            grant_type=grants.ClientCredentials.grant_type)

        request = FakeRequest(
            grant_type=grants.AuthorizeDelegate.grant_type,
            client=protected_service,
            scope=self.scope,
            requested_access=['r'],
            token=[token])

        grant = grants.ClientCredentials(request)
        with patch.object(grants.Service, 'get') as service_get:
            service_get.return_value = make_future(self.client)
            yield grant.verify_access(token)

        assert grant.verify_access_service.call_args[0][0].id == self.client.id
        assert grant.verify_access_hosted_resource.call_args[0][0].id == self.client.id


class TestAuthorizeDelegateGrant(AsyncTestCase):
    def setUp(self):
        super(TestAuthorizeDelegateGrant, self).setUp()

        self.scope = 'write[1234]'
        self.client = perch.Service(
            id='client_id',
            parent=ORGANISATION,
            organisation_id=ORGANISATION.id,
            state=perch.State.approved,
            service_type='external'
        )
        self.delegate = perch.Service(
            id='delegate_client_id',
            parent=ORGANISATION,
            organisation_id=ORGANISATION.id,
            state=perch.State.approved,
            service_type='onboarding',
            location='http://onboarding.test',
            permissions=[
                {
                    'type': 'organisation_id',
                    'value': ORGANISATION.id,
                    'permission': 'rw'
                }
            ]
        )
        delegate_scope = 'delegate[{}]:{}'.format(self.delegate.id, self.scope)
        self.client_token, expiry = generate_token(
            self.client,
            delegate_scope,
            grants.AuthorizeDelegate.grant_type)

        self.request = FakeRequest(
            grant_type=grants.AuthorizeDelegate.grant_type,
            client=self.delegate,
            scope=self.scope,
            assertion=[self.client_token])

    @gen_test
    def test_generate_token(self):
        grant = grants.AuthorizeDelegate(self.request)

        with patch.object(grants.Service, 'get') as get_srv:
            get_srv.return_value = make_future(self.client)

            token, expiry = yield grant.generate_token()

        decoded = decode_token(token)

        assert decoded['delegate'] is True
        assert decoded['client']['id'] == self.client.id
        assert decoded['sub'] == self.delegate.id
        assert str(decoded['scope']) == self.scope

    @gen_test
    def test_client_may_not_access_delegate(self):
        self.delegate.permissions = []
        grant = grants.AuthorizeDelegate(self.request)

        with patch.object(grants.Service, 'get') as get_srv:
            get_srv.return_value = make_future(self.client)

            with pytest.raises(grants.Unauthorized):
                yield grant.generate_token()

    @gen_test
    def test_missing_assertion(self):
        del self.request.body_arguments['assertion']
        grant = grants.AuthorizeDelegate(self.request)

        with pytest.raises(ValueError):
            yield grant.generate_token()

    @gen_test
    def test_empty_assertion(self):
        self.request.body_arguments['assertion'] = []
        grant = grants.AuthorizeDelegate(self.request)

        with pytest.raises(ValueError):
            yield grant.generate_token()

    @gen_test
    def test_invalid_assertion(self):
        self.request.body_arguments['assertion'] = ['invalid_token']
        grant = grants.AuthorizeDelegate(self.request)

        with pytest.raises(jwt.DecodeError):
            yield grant.generate_token()

    @gen_test
    def test_invalid_scope(self):
        self.request.body_arguments['scope'] = ['write[something_else]']
        grant = grants.AuthorizeDelegate(self.request)

        with pytest.raises(grants.Unauthorized):
            yield grant.generate_token()

    @gen_test
    def test_url_scope(self):
        delegate_scope = 'delegate[{}]:{}'.format(self.delegate.location,
                                                  self.scope)
        client_token, _ = generate_token(self.client, delegate_scope,
                                         grants.AuthorizeDelegate.grant_type)
        request = FakeRequest(
            grant_type=grants.AuthorizeDelegate.grant_type,
            client=self.delegate,
            scope=self.scope,
            assertion=[client_token])

        with patch.object(grants.Service, 'get') as get_srv:
            get_srv.return_value = make_future(self.client)
            grant = grants.AuthorizeDelegate(request)

            yield grant.generate_token()

    @gen_test
    def test_invalid_url_scope(self):
        delegate_scope = 'delegate[{}]:{}'.format('http://something.test',
                                                  self.scope)
        client_token, expiry = generate_token(
            self.client,
            delegate_scope,
            grants.AuthorizeDelegate.grant_type)
        request = FakeRequest(
            grant_type=grants.AuthorizeDelegate.grant_type,
            client=self.delegate,
            scope=self.scope,
            assertion=[client_token])

        grant = grants.AuthorizeDelegate(request)

        with patch.object(grants.Service, 'get') as get_srv:
            get_srv.return_value = make_future(self.client)
            grant = grants.AuthorizeDelegate(request)

            with pytest.raises(grants.Unauthorized):
                yield grant.generate_token()

    @patch.object(grants.AuthorizeDelegate, 'verify_access_service',
                  return_value=make_future(True))
    @patch.object(grants.AuthorizeDelegate, 'verify_access_hosted_resource',
                  return_value=make_future(True))
    @gen_test
    def test_verify_access(self, resource, service):
        protected_service = perch.Service(
            id='1234',
            location='http://test.client'
        )
        token, expiry = generate_token(
            self.client,
            self.scope,
            grant_type=grants.AuthorizeDelegate.grant_type,
            delegate_id=self.delegate.id)

        request = FakeRequest(
            grant_type=grants.AuthorizeDelegate.grant_type,
            client=protected_service,
            scope=self.scope,
            requested_access=['w'],
            token=[token])

        def get_service(_, service_id, *args, **kwargs):
            if service_id == self.delegate.id:
                return make_future(self.delegate)
            else:
                return make_future(self.client)

        with patch.object(grants.Service, 'get', classmethod(get_service)):
            grant = grants.AuthorizeDelegate(request)
            yield grant.verify_access(token)

        grant.verify_access_service.has_calls([
            call(self.delegate)
        ])

        assert grant.verify_access_service.call_args_list[1][0][0].id == self.client.id
        assert grant.verify_access_hosted_resource.call_args[0][0].id == self.client.id
