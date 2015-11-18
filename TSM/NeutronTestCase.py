__author__ = 'micucci'
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

import importlib
import logging
import datetime

from common.Exceptions import *
from common.CLI import LinuxCLI
from TestScenario import TestScenario

from VTM.VirtualTopologyManager import VirtualTopologyManager
from PTM.PhysicalTopologyManager import PhysicalTopologyManager

from TSM.TestCase import TestCase
from TSM.NeutronTestFixture import NeutronTestFixture

from VTM.NeutronAPI import setup_neutron, clean_neutron
from VTM.MNAPI import create_midonet_client, setup_main_tunnel_zone
from VTM.Guest import Guest

import neutronclient.v2_0.client as neutron_client

from collections import namedtuple

GuestData = namedtuple('GuestData', 'port vm ip')
""" :type: (str, Guest, str)"""
NetData = namedtuple('NetData', 'network subnet')
RouterData = namedtuple('RouterData', 'router if_list')


class NeutronTestCase(TestCase):

    def __init__(self, methodName='runTest'):
        super(NeutronTestCase, self).__init__(methodName)
        self.neutron_fixture = None
        """:type: NeutronTestFixture"""
        self.main_network = None
        self.main_subnet = None
        self.pub_network = None
        self.pub_subnet =None
        self.api = None
        """ :type: neutron_client.Client """
        self.mn_api = None

    @classmethod
    def _prepare_class(cls, current_scenario,
                       test_case_logger=logging.getLogger()):
        """
        :type current_scenario: TestScenario
        :type test_case_logger: logging.logger
        """
        super(NeutronTestCase, cls)._prepare_class(current_scenario, test_case_logger)

        cls.api = cls.vtm.get_client()
        """ :type: neutron_client.Client """
        cls.mn_api = create_midonet_client()

        # Only add the neutron-setup fixture once for each scenario.
        if 'neutron-setup' not in current_scenario.fixtures:
            test_case_logger.debug('Adding neutron-setup fixture for scenario: ' +
                                   type(current_scenario).__name__)
            neutron_fixture = NeutronTestFixture(cls.vtm, cls.ptm, current_scenario.LOG)
            current_scenario.add_fixture('neutron-setup', neutron_fixture)

    def run(self, result=None):
        """
        Special run override to make sure to set up neutron data prior to running
        the test case function.
        """
        self.neutron_fixture = self.current_scenario.get_fixture('neutron-setup')
        self.LOG.debug("Initializing Test Case Neutron Data from neutron-setup fixture")
        self.main_network = self.neutron_fixture.main_network
        self.main_subnet = self.neutron_fixture.main_subnet
        self.pub_network = self.neutron_fixture.pub_network
        self.pub_subnet = self.neutron_fixture.pub_subnet
        self.api = self.neutron_fixture.api
        self.mn_api = self.neutron_fixture.mn_api
        super(NeutronTestCase, self).run(result)

    #TODO: Change this to use the GuestData namedtuple
    def cleanup_vms(self, vm_port_list):
        """
        :type vm_port_list: list[(Guest, port)]
        """
        for vm, port in vm_port_list:
            try:
                self.LOG.debug('Shutting down vm on port: ' + str(port))
                if vm is not None:
                    vm.stop_capture(on_iface='eth0')
                    if port is not None:
                        vm.unplug_vm(port['id'])
                if port is not None:
                    self.api.delete_port(port['id'])
            finally:
                if vm is not None:
                    vm.terminate()