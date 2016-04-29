# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""Handler for providing and verifying OAuth authorization tokens"""
import logging

import jwt
from koi import exceptions
from tornado.gen import coroutine

from .base import AuthBaseHandler
from .. import oauth2


class VerifyHandler(AuthBaseHandler):
    """Responsible for verifying an OAuth token"""

    @coroutine
    def post(self):
        """Check whether a token is authorized to access the client"""
        try:
            token = self.request.body_arguments['token'][0]
        except (KeyError, IndexError):
            raise exceptions.HTTPError(400, 'Token is required')

        try:
            grant = oauth2.get_grant(self.request, token=token)
            yield grant.verify_access(token)
            self.finish({'status': 200, 'has_access': True})
        except oauth2.BadRequest as exc:
            raise exceptions.HTTPError(400, exc.args[0])
        except oauth2.Unauthorized as exc:
            logging.error('Unauthorized: %s', exc.args[0])
            self.finish({'status': 200, 'has_access': False})
        except jwt.InvalidTokenError as exc:
            logging.error('Invaild token: %s', exc.args[0])
            self.finish({'status': 200, 'has_access': False})


class TokenHandler(AuthBaseHandler):
    """Responsible for generating JSON web tokens"""
    @coroutine
    def post(self):
        """Return a token"""
        try:
            grant = oauth2.get_grant(self.request)
        except oauth2.InvalidGrantType:
            raise exceptions.HTTPError(400, 'invalid_grant')

        try:
            token, expiry = yield grant.generate_token()
        except (oauth2.InvalidScope, jwt.InvalidTokenError, ValueError) as exc:
            raise exceptions.HTTPError(400, exc.args[0])
        except oauth2.Unauthorized as exc:
            raise exceptions.HTTPError(403, exc.args[0])

        self.finish({
            'status': 200,
            'access_token': token,
            'token_type': 'bearer',
            'expiry': expiry
        })
