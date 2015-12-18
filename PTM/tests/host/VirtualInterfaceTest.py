__author__ = 'micucci'

import unittest
import time

from common.CLI import *
from PTM.host.Host import Host
from PTM.host.VirtualInterface import VirtualInterface
from PTM.host.Interface import Interface


class VirtualInterfaceTest(unittest.TestCase):
    def test_create_no_peer(self):
        cli = LinuxCLI(log_cmd=True)
        h = Host('test', None, cli, lambda n: None, lambda n: None)
        i = VirtualInterface(name='testi', host=h, ip_addr=['192.168.0.2'])

        i.create()  # should skip setting peer on host

        time.sleep(1)
        self.assertTrue(cli.grep_cmd('ip l', 'testi'))
        self.assertTrue(cli.grep_cmd('ip l', i.peer_name))

        i.up()  # should still work for near end device
        time.sleep(1)

        self.assertTrue(cli.grep_cmd('ip l | grep testi', 'UP'))

        i.down()
        time.sleep(1)

        self.assertFalse(cli.grep_cmd('ip l | grep testi', 'state UP'))

        i.remove()

        self.assertFalse(cli.grep_cmd('ip l', 'testi'))

    def test_create_with_host(self):
        h = Host('test', None, LinuxCLI(), lambda n: None, lambda n: None)
        h2 = Host('test2', None, NetNSCLI('test2'), CREATENSCMD, REMOVENSCMD)

        h2.create()

        p = Interface(name='testp', host=h2, ip_addr=['10.0.0.1'])
        i = VirtualInterface(name='testi', host=h, ip_addr=['192.168.0.2'], far_interface=p)

        i.create()  # should create and set peer on far host

        self.assertTrue(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertTrue(LinuxCLI().grep_cmd('ip l', 'testi'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi.p'))

        i.config_addr()
        p.up()
        p.config_addr()

        self.assertTrue(h2.cli.grep_cmd('ip a | grep testp | grep inet', '10.0.0.1'))

        i.remove()  # should remove both interfaces

        self.assertFalse(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi'))

        h2.remove()

    def test_add_del_ip(self):
        h = Host('test', None, LinuxCLI(), lambda n: None, lambda n: None)
        h2 = Host('test2', None, NetNSCLI('test2'), CREATENSCMD, REMOVENSCMD)

        h2.create()

        p = Interface(name='testp', host=h2, ip_addr=['10.0.0.1'])
        i = VirtualInterface(name='testi', host=h, ip_addr=[], far_interface=p)

        i.create()  # should create and set peer on far host

        self.assertTrue(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertTrue(LinuxCLI().grep_cmd('ip l', 'testi'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi.p'))

        i.config_addr()
        p.up()

        # the far iface should be controllable on its own just like any interface
        p.add_ip('192.168.1.2')

        self.assertTrue(h2.cli.grep_cmd('ip a | grep testp | grep inet | sed -e "s/^ *//" | cut -f 2 -d " "',
                                        '192.168.1.2'))

        p.del_ip('192.168.1.2')

        self.assertFalse(h2.cli.grep_cmd('ip a | grep testp | grep inet | sed -e "s/^ *//" | cut -f 2 -d " "',
                                         '192.168.1.2'))

        i.remove()  # should remove both interfaces

        self.assertFalse(h2.cli.grep_cmd('ip l', 'testp'))
        self.assertFalse(LinuxCLI().grep_cmd('ip l', 'testi'))

        h2.remove()


    def tearDown(self):
        LinuxCLI().cmd('ip l del testi')
        LinuxCLI().cmd('ip netns del test2')

from CBT.UnitTestRunner import run_unit_test
run_unit_test(VirtualInterfaceTest)
