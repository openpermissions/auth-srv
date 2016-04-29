# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import calendar
from datetime import datetime, timedelta

import koi
import jwt
import perch
import pytest
from mock import patch

from auth.oauth2 import token as _token
from auth.oauth2.token import generate_token, decode_token


EXPIRY = 30
CLIENT = perch.Service(
    id='client_id',
    service_type='client service type',
    organisation_id='client organisation',
    something_else='test'
)
SCOPE = 'read'
NOW = datetime.utcnow()

options_patch = patch('auth.oauth2.token.options')
datetime_patch = patch('auth.oauth2.token.datetime')


def setup():
    options = options_patch.start()
    options.ssl_key = None
    options.ssl_cert = None
    options.token_expiry = EXPIRY
    options.url_auth = 'https://localhost:8006'

    dt = datetime_patch.start()
    dt.utcnow.return_value = NOW


def teardown():
    options_patch.stop()
    datetime_patch.stop()


@patch.object(_token.jwt, 'encode', wraps=_token.jwt.encode)
def test_encode_token(encode):
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')

    decoded = jwt.decode(token, verify=False)
    expected_expiry = calendar.timegm(NOW.timetuple()) + EXPIRY * 60
    data = {
        'exp': expected_expiry,
        'iss': 'localhost:8006/token',
        'aud': 'localhost:8006/verify',
        'sub': CLIENT.id,
        'client': {
            'id': CLIENT.id,
            'service_type': CLIENT.service_type,
            'organisation_id': CLIENT.organisation_id,
        },
        'scope': SCOPE,
        'grant_type': 'grant_type',
        'delegate': False
    }

    assert decoded == data
    assert encode.call_count == 1
    assert encode.call_args_list[0][-1] == {'algorithm': 'RS256'}
    assert expiry == expected_expiry


def test_encode_delegate_token():
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type', 'delegate id')

    decoded = jwt.decode(token, verify=False)

    assert decoded['delegate'] is True
    assert decoded['sub'] == 'delegate id'


@patch.object(_token.jwt, 'decode', wraps=_token.jwt.decode)
def test_decode_token(decode):
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')

    decode_token(token)

    assert decode.call_count == 1
    assert decode.call_args_list[0][-1] == {'algorithms': ['RS256'],
                                            'audience': _token.audience(),
                                            'issuer': _token.issuer(),
                                            'verify': True}


def test_decode_token_invalid_issuer():
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')

    with patch.object(_token, 'issuer', return_value='test'):
        with pytest.raises(jwt.InvalidIssuerError):
            decode_token(token)


def test_decode_token_invalid_audience():
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')

    with patch.object(_token, 'audience', return_value='test'):
        with pytest.raises(jwt.InvalidAudience):
            decode_token(token)


def test_decode_token_different_public_key():
    token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')

    with patch.object(_token, 'LOCALHOST_CRT', koi.CLIENT_CRT):
        with pytest.raises(jwt.DecodeError):
            decode_token(token)


def test_decode_expired_token():
    in_the_past = NOW - timedelta(minutes=EXPIRY * 2 + 1)
    with patch.object(_token.datetime, 'utcnow', return_value=in_the_past):
        token, expiry = generate_token(CLIENT, SCOPE, 'grant_type')
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_missing_sub():
    client = perch.Service(**CLIENT._resource.copy())
    client.id = None
    token, expiry = generate_token(client, SCOPE, 'grant_type')

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_token(token)
