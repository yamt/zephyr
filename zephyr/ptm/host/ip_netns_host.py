# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zephyr.common.cli import CREATENSCMD
from zephyr.common.cli import NetNSCLI
from zephyr.common.cli import REMOVENSCMD
from zephyr.ptm.host.host import Host


class IPNetNSHost(Host):
    def __init__(self, name, ptm):
        """
        :type name: str
        :type ptm: PhysicalTopologyManager
        """
        super(IPNetNSHost, self).__init__(name, ptm, NetNSCLI(name),
                                          CREATENSCMD, REMOVENSCMD)
        self.on_namespace = True
