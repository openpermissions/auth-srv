# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""Configures and starts up the Authentication Service.
"""
import os.path

import koi
import tornado.ioloop
from tornado.options import options

from . import __version__
from .controllers import root_handler, authorize

# directory containing the config files
CONF_DIR = os.path.join(os.path.dirname(__file__), '../config')

APPLICATION_URLS = [
    (r"", root_handler.RootHandler, {'version': __version__}),
    (r"/verify", authorize.VerifyHandler),
    (r"/token", authorize.TokenHandler),
]


def main():
    """
    The entry point for the Authentication service.
    This will load the configuration files and start a Tornado webservice
    with one or more sub processes.

    NOTES:
    tornado.options.parse_command_line(final=True)
    Allows you to run the service with custom options.

    Examples:
        Change the logging level to debug:
            + python auth --logging=DEBUG
            + python auth --logging=debug

        Configure custom syslog server:
            + python auth --syslog_host=54.77.151.169
    """
    koi.load_config(CONF_DIR)
    app = koi.make_application(
        __version__,
        options.service_type,
        APPLICATION_URLS)
    server = koi.make_server(app, CONF_DIR)

    # Forks multiple sub-processes, one for each core
    server.start(int(options.processes))

    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':      # pragma: no cover
    main()                      # pragma: no cover
