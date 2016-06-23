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

import operator

from zephyr.common import utils
from zephyr.tsm.neutron_test_case import NeutronTestCase
from zephyr.tsm.neutron_test_case import require_extension
from zephyr.tsm import test_case


class TestFWaaSLogging(NeutronTestCase):
    def __init__(self, method_name):
        super(TestFWaaSLogging, self).__init__(method_name=method_name)
        self.vm1 = None
        self.vm2 = None
        self.ip1 = None
        self.ip2 = None
        self.fw = None
        self.near_far_router = None

    def setUp(self):
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

        self.near_far_router = self.create_router(
            'near_far_router',
            priv_sub_ids=[far_sub['id'], near_sub['id']])

        second_vm = "cmp1"
        if (self._testMethodName ==
                "test_logging_basic_accept_two_computes"):
            second_vm = "cmp2"

        (port1, self.vm1, self.ip1) = self.create_vm_server(
            'vm1',
            net_id=near_net['id'],
            gw_ip=near_sub['gateway_ip'],
            hv_host='cmp1')
        (port2, self.vm2, self.ip2) = self.create_vm_server(
            'vm2',
            net_id=far_net['id'],
            gw_ip=far_sub['gateway_ip'],
            hv_host=second_vm)

        fwp = self.create_firewall_policy('POLICY')
        self.fw = self.create_firewall(
            fwp['id'], router_ids=[self.near_far_router['id']])
        self.create_firewall_rule(
            action='allow', protocol='tcp', dest_port=7777)

    def check_fwaas_logs(self, uuid, accept, drop, host='cmp1'):
        cmp_host = self.ptm.hosts_by_name[host]
        """ :type: zephyr_ptm.ptm.host.host.Host"""
        fwaas_logs = cmp_host.fetch_resources_from_apps(
            resource_name='fwaas_log',
            uuid=uuid)
        self.assertEqual(1, len(fwaas_logs))
        self.assertTrue(
            utils.check_string_for_tag(fwaas_logs[0], 'ACCEPT', accept))
        self.assertTrue(
            utils.check_string_for_tag(fwaas_logs[0], 'DROP', drop))

    @require_extension("fwaas")
    def test_logging_basic_accept(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)

    @require_extension("fwaas")
    @test_case.require_topology_feature('compute_hosts', operator.gt, 1)
    def test_logging_basic_accept_two_computes(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)

    @require_extension("fwaas")
    def test_logging_basic_drop(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='DROP', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=0, drop=1)

    @require_extension("fwaas")
    def test_logging_all(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=1)

    @require_extension("fwaas")
    def test_logging_two_fw(self):
        fwp2 = self.create_firewall_policy('POLICY')
        fw2 = self.create_firewall(
            fwp2['id'], router_ids=[self.near_far_router['id']])
        self.create_firewall_rule(
            action='allow', protocol='tcp', dest_port=8888)

        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        fw_log_obj = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])
        fw_log_obj2 = self.create_firewall_log(
            fw_event='ALL', res_id=log_res['id'], fw_id=fw2['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=1)
        self.check_fwaas_logs(uuid=fw_log_obj2['id'], accept=1, drop=1)

    @require_extension("fwaas")
    def test_logging_update_event(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)

        self.update_firewall_log(
            fwlog_id=fw_log_obj['id'],
            fw_event='ALL', res_id=log_res['id'], fw_id=self.fw['id'])

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=1)

    @require_extension("fwaas")
    def test_logging_update_fw_id(self):
        fwp2 = self.create_firewall_policy('POLICY')
        fw2 = self.create_firewall(
            fwp2['id'], router_ids=[self.near_far_router['id']])
        self.create_firewall_rule(
            action='allow', protocol='tcp', dest_port=8888)

        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)
        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)

        self.update_firewall_log(
            fwlog_id=fw_log_obj['id'],
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=fw2['id'])

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=2, drop=0)

    @require_extension("fwaas")
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

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)
        self.check_fwaas_logs(uuid=fw_log_obj2['id'], accept=0, drop=1)

    @require_extension("fwaas")
    def test_logging_fail_two_fw_loggers(self):
        log_res = self.create_logging_resource(
            name='fw_logging',
            enabled=True)

        fw_log_obj = self.create_firewall_log(
            fw_event='ACCEPT', res_id=log_res['id'], fw_id=self.fw['id'])
        fw_log_obj2 = self.create_firewall_log(
            fw_event='DROP', res_id=log_res['id'], fw_id=self.fw['id'])

        self.vm2.start_echo_server(port=7777, echo_data='pong')
        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=7777)
        self.assertEqual('ping:pong', reply)

        reply = self.vm1.send_echo_request(dest_ip=self.ip2, dest_port=8888)
        self.assertEqual('', reply)

        self.check_fwaas_logs(uuid=fw_log_obj['id'], accept=1, drop=0)
        self.check_fwaas_logs(uuid=fw_log_obj2['id'], accept=0, drop=1)
