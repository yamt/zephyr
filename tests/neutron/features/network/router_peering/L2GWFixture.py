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

from zephyr.ptm.fixtures.service_fixture import ServiceFixture
from zephyr.common.cli import LinuxCLI


class L2GWFixture(ServiceFixture):
    def __init__(self):
        super(L2GWFixture, self).__init__()

    def setup(self):
        LinuxCLI().cmd("neutron-l2gw-db-manage --config-file /etc/neutron/neutron.conf upgrade head")
        LinuxCLI().cmd("neutron-db-manage --service fwaas upgrade head")

    def teardown(self):
        pass
