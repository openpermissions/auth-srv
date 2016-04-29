# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

import base64
from urllib import unquote_plus

from koi import exceptions
from koi.base import JsonHandler, CorsHandler
from perch import Service
from tornado.gen import coroutine


class AuthBaseHandler(JsonHandler, CorsHandler):
    client_organisation = None

    @coroutine
    def prepare(self):
        if self.request.method == 'OPTIONS':
            return

        auth_header = self.request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            raise exceptions.HTTPError(401, 'Unauthenticated')

        decoded = unquote_plus(base64.decodestring(auth_header[6:]))
        client_id, client_secret = decoded.split(':', 1)

        service = yield Service.authenticate(client_id, client_secret)
        if not service:
            raise exceptions.HTTPError(401, 'Unauthenticated')

        self.request.client_id = client_id
        self.request.client = service

        grant_type = self.request.body_arguments.get('grant_type', [None])[0]
        self.request.grant_type = grant_type
