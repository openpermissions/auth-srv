# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import pytest
from mock import patch
import perch
from perch import exceptions
from tornado.gen import coroutine, Return
from tornado.testing import AsyncTestCase, gen_test

from auth import oauth2
from auth.oauth2.scope import Scope, READ, WRITE, DELEGATE


class TestScope(AsyncTestCase):
    def setUp(self):
        super(TestScope, self).setUp()
        self.client = perch.Service(
            id='client id',
            organisation_id='org1',
            service_type='external'
        )
        self.repositories = [{
            'type': 'repository',
            'id': 'repo1',
            'permissions': [
                {'type': 'organisation_id',
                 'value': self.client.organisation_id,
                 'permission': 'rw'}
            ]
        }, {
            'type': 'repository',
            'id': 'repo2',
        }, {
            'type': 'repository',
            'id': 'repo3',
            'permissions': [
                {'type': 'organisation_id',
                 'value': self.client.organisation_id,
                 'permission': 'rw'}
            ]
        }]
        self.services = [{
            'type': 'service',
            'id': 'service1',
            'location': 'http://service.test',
            'permissions': [
                {'type': 'organisation_id',
                 'value': self.client.organisation_id,
                 'permission': 'rw'}
            ]
        }, {
            'type': 'service',
            'id': 'service2',
            'location': 'http://service2test',
        }, {
            'type': 'service',
            'id': 'service3',
            'location': 'http://service3.test',
            'permissions': [
                {'type': 'service_type',
                 'value': self.client.service_type,
                 'permission': 'rw'}
            ]
        }]
        self.resources = {x['id']: x for x in self.services + self.repositories}
        self.locations = {x['location']: x for x in self.services}

        view_patch = patch(
            'auth.oauth2.scope.views.service_and_repository.first',
            coroutine(lambda key: {'value': self.resources[key]})
        )
        view_patch.start()

        @coroutine
        def by_location(cls, url):
            try:
                raise Return(cls(**self.locations[url]))
            except KeyError:
                raise exceptions.NotFound()

        service_patch = patch(
            'auth.oauth2.scope.Service.get_by_location',
            classmethod(by_location)
        )
        service_patch.start()

    def tearDown(self):
        super(TestScope, self).tearDown()
        patch.stopall()

    @coroutine
    def get_docs(self, db_name, ids):
        raise Return([self.resources[x] for x in ids])

    @coroutine
    def get_by_location(self, url):
        raise Return([{'doc': self.services[0]}])

    def test_init(self):
        scope = Scope('read write[1234] delegate[5678]:write[0987] '
                      'delegate[5678]:read[1234] read[4793] read[1234]')
        assert scope.read is True
        assert scope.delegates == {'5678': {('w', None), ('r', None)}}
        assert scope.resources == {
            '1234': {('r', None), ('w', None), ('r', '5678')},
            '4793': {('r', None)},
            '0987': {('w', '5678')},
        }

    def test_init_only_specific_read(self):
        scope = Scope('write[1234] delegate[5678]:write[0987] read[1234]')
        assert scope.read is False
        assert scope.resources['1234'] == {('r', None),
                                           ('w', None)}

    @gen_test
    def test_invalid_action(self):
        # parametrize doesn't work with gen_test?
        scopes = [
            'invalid',
            READ + ' invalid',
            'invalid[read]'
        ]

        for scope in scopes:
            with pytest.raises(oauth2.InvalidScope):
                yield Scope(scope).validate(self.client)

    @gen_test
    def test_write_missing_elements(self):
        with pytest.raises(oauth2.InvalidScope):
            yield Scope(WRITE).validate(self.client)

    @gen_test
    def test_delegate_mising_elements(self):
        scopes = [
            DELEGATE,
            '{}[1234]'.format(DELEGATE),
            '{}:1234:{}'.format(DELEGATE, WRITE)
        ]

        for scope in scopes:
            with pytest.raises(oauth2.InvalidScope):
                yield Scope(scope).validate(self.client)

    @gen_test
    def test_client_has_access_to_repository(self):
        yield Scope('write[repo1]').validate(self.client)

    @gen_test
    def test_client_has_access_to_read_repository(self):
        yield Scope('read[repo1]').validate(self.client)

    @gen_test
    def test_client_has_access_to_rw_repository(self):
        yield Scope('write[repo1] read[repo1]').validate(self.client)

    @gen_test
    def test_client_has_access_to_service(self):
        yield Scope('write[service1]').validate(self.client)

    @gen_test
    def test_client_has_access_to_url(self):
        yield Scope('write[http://service.test]').validate(self.client)

    @gen_test
    def test_location_does_not_exist(self):
        with pytest.raises(oauth2.InvalidScope):
            yield Scope('write[http://unknown.test]').validate(self.client)

    @gen_test
    def test_client_has_access_to_more_than_one_resource(self):
        scope = Scope('write[repo1] read[service1]')
        yield scope.validate(self.client)

    @gen_test
    def test_do_not_have_access_to_a_resource(self):
        with pytest.raises(oauth2.Unauthorized):
            yield Scope('write[repo2]').validate(self.client)

    @gen_test
    def test_do_not_have_access_to_one_of_many_resources(self):
        with pytest.raises(oauth2.Unauthorized):
            yield Scope('write[repo1] write[repo2]').validate(self.client)

    @gen_test
    def test_have_access_to_delegate(self):
        yield Scope('delegate[service1]:write[repo1]').validate(self.client)

    @gen_test
    def test_have_access_to_more_than_one_delegate(self):
        scope = 'delegate[service1]:write[repo1] delegate[service3]:write[repo3]'
        yield Scope(scope).validate(self.client)

    @gen_test
    def test_do_not_have_access_to_a_delegate(self):
        with pytest.raises(oauth2.Unauthorized):
            yield Scope('delegate[service2]:write[repo1]').validate(self.client)


@pytest.mark.parametrize('access,scope,expected', [
    ('r', 'read', True),
    ('rw', 'read', True),
    ('w', 'read', False),
    ('r', 'read[something]', True),
    ('rw', 'read[something]', True),
    ('w', 'read[something]', False),
    ('r', 'write[something]', False),
    ('rw', 'write[something]', True),
    ('w', 'write[something]', True),
    ('r', 'delegate[something]:read[other]', True),
    ('rw', 'delegate[something]:read[other]', True),
    ('w', 'delegate[something]:read[other]', False),
    ('r', 'delegate[something]:write[other]', False),
    ('rw', 'delegate[something]:write[other]', True),
    ('w', 'delegate[something]:write[other]', True),
    ('r', 'delegate[other]:read[something]', False),
    ('rw', 'delegate[other]:read[something]', False),
    ('w', 'delegate[other]:read[something]', False),
    ('r', 'delegate[other]:write[something]', False),
    ('rw', 'delegate[other]:write[something]', False),
    ('w', 'delegate[other]:write[something]', False),
])
def test_within_read_scope(access, scope, expected):
    scope = oauth2.Scope(scope)

    assert scope.within_scope(access, 'something') is expected
