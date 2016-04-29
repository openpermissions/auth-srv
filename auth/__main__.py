#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""Used to start the service from the parent directory using command:
    python auth/
"""

import os

from auth.app import main, CONF_DIR
from koi import commands


if __name__ == '__main__':  # pragma: no cover
    commands_dir = os.path.join(os.path.dirname(__file__), 'commands')
    commands.cli(main, conf_dir=CONF_DIR, commands_dir=commands_dir)
