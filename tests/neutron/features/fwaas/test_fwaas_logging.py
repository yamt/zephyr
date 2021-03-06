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

from zephyr.common import exceptions
from zephyr.common import utils
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm import test_case
from zephyr.vtm import fwaas_fixture


class TestFWaaSLogging(NeutronTestCase):
    def __init__(self, method_name):
        super(TestFWaaSLogging, self).__init__(method_name=method_name)
        self.vm1 = None
        self.vm2 = None
        self.ip1 = None
        self.ip2 = None
        self.fw = None
        self.near_far_router = None

    def make_simple_topology(self, name='A'):
        near_net = self.create_network('near_net')
        near_sub = self.create_subnet(
            'near_sub',
            net_id=near_net['id'],
            cidr='192.179.100.0/24')

        far_net = self.create_network('far_net')
        far_sub = self.create_subnet(
            'far_sub',
            net_id=far_net['id'],
            cidr='192.179.200.0/24')

        near_far_router = self.create_router(
            'near_far_router',
            priv_sub_ids=[far_sub['id'], near_sub['id']])

        (port1, vm1, ip1) = self.create_vm_server(
            'vm1' + name,
            net_id=near_net['id'],
            gw_ip=near_sub['gateway_ip'],
            port_security_enabled=False)

        second_vm = vm1.get_hypervisor_name()

        if (self._testMethodName ==
                "test_logging_basic_accept_two_computes"):
            second_vm = '!' + second_vm

        (port2, vm2, ip2) = self.create_vm_server(
            'vm2' + name,
            net_id=far_net['id'],
            gw_ip=far_sub['gateway_ip'],
            hv_host=[second_vm],
            port_security_enabled=False)

        fwp = self.create_firewall_policy('POLICY')
        fw = self.create_firewall(
            fwp['id'], router_ids=[near_far_router['id']])
        fwr_accept = self.create_firewall_rule(
            action='allow', protocol='tcp', dest_port=7777)
        fwr_accept_ret = self.create_firewall_rule(
            action='allow', protocol='tcp', src_port=7777)
        self.insert_firewall_rule(
            fw_policy_id=fwp['id'], fw_rule_id=fwr_accept['id'])
        self.insert_firewall_rule(
            fw_policy_id=fwp['id'], fw_rule_id=fwr_accept_ret['id'])
        return vm1, ip1, vm2, ip2, fw, near_far_router

    def setUp(self):
        fwaas_fixture.FWaaSFixture().setup()
        (self.vm1, self.ip1, self.vm2, self.ip2, self.fw,
         self.near_far_router) = self.make_simple_topology()

    def check_fwaas_logs(self, uuid, accept, drop, host='cmp1', exact=False,
                         exist=True):
        cmp_host = self.vtm.get_host(host)
        """
        :type: zephyr.underlay.underlay_host.UnderlayHost
        """
        fwaas_logs = cmp_host.fetch_file(
            file_type='fwaas_log', uuid=uuid)
        if exist:
            self.assertEqual(1, len(fwaas_logs))
            accepted = sum(e['result'] == 'ACCEPT' for e in fwaas_logs[0])
            dropped = sum(e['result'] == 'DROP' for e in fwaas_logs[0])
            if exact:
                self.assertEqual(accept, accepted)
                self.assertEqual(drop, dropped)
            else:
                self.assertGreaterEqual(accepted, accept)
                self.assertGreaterEqual(dropped, drop)
        else:
            self.assertEqual(0, len(fwaas_logs))

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_basic_accept(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        self.vm2.start_echo_server(ip_addr=self.ip2, port=8888,
                                   echo_data='pong2')

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1', 'cmp2'])
    def test_logging_basic_accept_two_computes(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_basic_drop(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='DROP', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=0, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_all(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_update_enabled(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=False)
        fw_log_obj = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=0, drop=0,
                              exact=True, exist=False)

        self.update_logging_resource(log_res['id'], enabled=True)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_two_fw(self):
        (vm1_2, ip1_2, vm2_2,
         ip2_2, fw_2,
         near_far_router_2) = self.make_simple_topology(name='B')

        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        log_res_2 = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        fw_log_obj = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])
        fw_log_obj2 = self.create_firewall_log(
            fw_event='ALL', res_id=log_res_2['id'], fw_id=fw_2['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        vm2_2.start_echo_server(
            ip_addr=ip2_2, port=7777, echo_data='pong')
        reply = vm1_2.send_echo_request(dest_ip=ip2_2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        try:
            reply = vm1_2.send_echo_request(dest_ip=ip2_2,
                                            dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(
            uuid=fw_log_obj['id'],
            host=self.vm1.get_hypervisor_name(),
            accept=2, drop=1)
        self.check_fwaas_logs(
            uuid=fw_log_obj2['id'],
            host=vm1_2.get_hypervisor_name(),
            accept=2, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_update_event(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(ip_addr=self.ip2, port=7777,
                                   echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)

        self.update_firewall_log(
            fwlog_id=fw_log_obj['id'],
            fw_event='ALL', res_id=log_res['id'])

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=4, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_fail_two_log_res(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        log_res2 = self.create_logging_resource(
            name='fw_logging2',
            enabled=True)

        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])
        fw_log_obj2 = self.create_firewall_log(
            fw_event='DROP', res_id=log_res2['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(
            ip_addr=self.ip2, port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)
        self.check_fwaas_logs(uuid=fw_log_obj2['id'], accept=0, drop=1)

    @require_extension("fwaas")
    @test_case.require_hosts(['cmp1'])
    def test_logging_fail_two_fw_loggers(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])
        fw_log_obj2 = self.create_firewall_log(
            fw_event='DROP', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(
            ip_addr=self.ip2, port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        try:
            reply = self.vm1.send_echo_request(dest_ip=self.ip2,
                                               dest_port=8888)
            self.assertEqual('', reply)
        except exceptions.SubprocessFailedException:
            pass

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)
        self.check_fwaas_logs(uuid=fw_log_obj2['id'], accept=0, drop=1)
