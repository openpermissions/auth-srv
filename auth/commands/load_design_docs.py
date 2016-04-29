# -*- coding: utf-8 -*-
# Copyright 2016 Open Permissions Platform Coalition
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.

"""
design doc loader
"""
import click
from perch.views import load_design_docs


@click.command(help='load design docs')
@click.argument('files', nargs=-1, type=click.File('rb'))
def cli(files):
    print 'loading design docs'
    load_design_docs()
    print 'design docs successfully loaded'

