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

from zephyr.common.cli import LinuxCLI
from zephyr_ptm.ptm.host.host import Host


class RootHost(Host):
    def __init__(self, name, ptm):
        """
        Implement a basic Host which just accesses the local Linux OS
        without using IP Net namespaces
        :param name: str
        :param ptm: PhysicalTopologyManager
        :return:
        """
        super(RootHost, self).__init__(name, ptm, LinuxCLI(),
                                       lambda n: None, lambda n: None)
