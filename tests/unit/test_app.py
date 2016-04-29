# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""Unit tests for the main application code"""
from mock import patch

import auth.app


@patch('auth.app.options')
@patch('tornado.ioloop.IOLoop.instance')
@patch('auth.app.koi.make_server')
@patch('auth.app.koi.load_config')
def test_main_configure_and_run_service(load_config, make_server,
                                        instance, options):
    server = make_server.return_value
    options.processes = 1
    # MUT
    auth.app.main()

    load_config.call_count == 1
    make_server.call_count == 1
    server.start.assert_called_once_with(1)
    instance.call_count == 1
