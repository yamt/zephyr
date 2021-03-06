# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class PTMObject(object):
    def __init__(self, name, cli):
        super(PTMObject, self).__init__()
        self.name = name
        """ :type: str """
        self.cli = cli
        """ :type: LinuxCLI """

    def get_name(self):
        return self.name

    def get_cli(self):
        return self.cli

    def print_config(self, indent=0):
        pass
