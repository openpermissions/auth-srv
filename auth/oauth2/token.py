# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""Create and decode JSON Web Tokens"""
import calendar
from datetime import datetime, timedelta
from urlparse import urlparse

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from koi import LOCALHOST_CRT, LOCALHOST_KEY
from tornado.options import options

from .scope import Scope

ALGORITHM = 'RS256'


def base_uri():
    auth_url = urlparse(getattr(options, 'url_auth', 'localhost'))
    base_uri = '/'.join([auth_url.netloc, auth_url.path])

    return base_uri.rstrip('/')


def issuer():
    return '/'.join([base_uri(), 'token'])


def audience():
    return '/'.join([base_uri(), 'verify'])


def generate_token(client, scope, grant_type, delegate_id=None):
    """
    Create an OAuth2 JSON Web Token, containing the scope & client details

    See https://tools.ietf.org/html/rfc7523 for specifications

    :param client: dict, the authenticated client
    :param scope: the scope (should already be validated)
    :param delegate_id: (optional) the ID of a delegate. If the token is
        generated for a delegate it should be included so that the delegate
        ID is included as the "sub" claim
    :returns: (token, expiry datetime in seconds since the epoch)
    """
    key_file = getattr(options, 'ssl_key', None) or LOCALHOST_KEY
    with open(key_file) as f:
        key = f.read()

    if delegate_id:
        subject = delegate_id
        delegate = True
    else:
        subject = client.id
        delegate = False

    minutes = getattr(options, 'token_expiry', 10)
    expiry = datetime.utcnow() + timedelta(minutes=minutes)
    # NOTE: exp, iss, aud & sub are required by rfc7523, and client, scope &
    # delegate are our private claims
    data = {
        'exp': expiry,
        'iss': issuer(),
        'aud': audience(),
        'sub': subject,
        'client': {
            'id': client.id,
            'service_type': client.service_type,
            'organisation_id': client.organisation_id,
        },
        'scope': str(scope),
        'grant_type': grant_type,
        'delegate': delegate
    }

    return (jwt.encode(data, key, algorithm=ALGORITHM),
            calendar.timegm(expiry.timetuple()))


def decode_token(token):
    """
    Get the organisation ID from a token

    :param token: a JSON Web Token
    :returns: str, organisation ID
    :raises:
        jwt.DecodeError: Invalid token or not signed with our key
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidAudienceError: Invalid "aud" claim
        jwt.InvalidIssuerError: Invalid "iss" claim
        jwt.MissingRequiredClaimError: Missing a required claim
    """
    cert_file = getattr(options, 'ssl_cert', None) or LOCALHOST_CRT
    with open(cert_file) as f:
        cert = load_pem_x509_certificate(f.read(), default_backend())
        public_key = cert.public_key()

    payload = jwt.decode(token,
                         public_key,
                         audience=audience(),
                         issuer=issuer(),
                         algorithms=[ALGORITHM],
                         verify=True)

    if not payload.get('sub'):
        raise jwt.MissingRequiredClaimError('"sub" claim is required')

    payload['scope'] = Scope(payload['scope'])

    return payload
