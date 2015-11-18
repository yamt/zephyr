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


from common.Exceptions import *
from common.IP import IP
from common.LogManager import LogManager

from PTM.PhysicalTopologyManager import PhysicalTopologyManager
from PTM.ComputeHost import ComputeHost
from PTM.ComputeHost import VMHost

from VTM.Guest import Guest


class VirtualTopologyManager(object):
    global_vm_id = 0

    def __init__(self,
                 physical_topology_manager,
                 client_api_impl=None,
                 log_manager=None):

        self.client_api_impl = client_api_impl
        self.physical_topology_manager = physical_topology_manager
        """ :type: PhysicalTopologyManager"""
        self.log_manager = log_manager if log_manager is not None else LogManager(root_dir='logs')
        """ :type: LogManager"""

    def get_client(self):
        return self.client_api_impl

    def create_vm(self, ip, gw_ip=None, preferred_hv_host=None, preferred_name=None):
        """
        Creates a guest VM on the Physical Topology and returns the Guest
        object representing the VM as part of the virtual topology.
        :param ip: str IP Address to use for the VM (required)
        :param preferred_hv_host: str: Hypervisor to use, otherwise the least-loaded HV host is chosen.
        :param preferred_name: str: Name to use for the VM.  Otherwise one is generated.
        :return: Guest
        """
        self.physical_topology_manager.LOG.debug("Creating VM on IP: " + str(ip))
        if preferred_hv_host is None:
            # Pick the HV with the fewest running VMs
            least_busy_hv = None
            for hv in self.physical_topology_manager.hypervisors.itervalues():
                if least_busy_hv is None or least_busy_hv > hv.get_vm_count():
                    least_busy_hv = hv
            if least_busy_hv is None:
                raise ObjectNotFoundException('No suitable hypervisor found to launch VM')
            start_hv = least_busy_hv
        else:
            if preferred_hv_host not in self.physical_topology_manager.hypervisors:
                raise ObjectNotFoundException('Requested host to start VM: ' + preferred_hv_host + ' not found')
            start_hv = self.physical_topology_manager.hypervisors[preferred_hv_host]

        if preferred_name is not None:
            vm_name = preferred_name
        else:
            vm_name = 'vm_' + str(VirtualTopologyManager.global_vm_id)
            VirtualTopologyManager.global_vm_id += 1

        self.physical_topology_manager.LOG.debug("Starting VM with name: " + vm_name + " and IP: " +
                                                 str(ip) + " on hypervisor: " + start_hv.name)
        new_vm = start_hv.create_vm(vm_name)
        """ :type: VMHost """
        real_ip = IP.make_ip(ip)
        new_vm.create_interface('eth0', ip_list=[real_ip])
        if gw_ip is None:
            # Figure out a default gw based on IP, usually (IP & subnet_mask + 1)
            subnet_mask = [255, 255, 255, 255]
            if real_ip.subnet != "":
                smask = int(real_ip.subnet)
                subnet_mask = []

                current_mask = smask
                for i in range(0, 4):
                    if current_mask > 8:
                        subnet_mask.append(255)
                    else:
                        lastmask = 0
                        for i in range(0, current_mask):
                            lastmask += pow(2, 8-(i+1))
                        subnet_mask.append(lastmask)
                    current_mask -= 8

            split_ip = real_ip.ip.split(".")
            gw_ip_split = []
            for ip_part in split_ip:
                gw_ip_split.append(int(ip_part) & subnet_mask[len(gw_ip_split)])

            gw_ip_split[3] += 1
            gw_ip = '.'.join(map(lambda x: str(x), gw_ip_split))

        self.physical_topology_manager.LOG.debug("Adding default route for VM: " + gw_ip)

        new_vm.add_route(gw_ip=IP.make_ip(gw_ip))
        return Guest(new_vm)