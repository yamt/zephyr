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

import socket
import time

from zephyr.common import cli
from zephyr.common import exceptions
from zephyr.common.file_location import *
from zephyr_ptm.ptm.application import application
from zephyr_ptm.ptm.physical_topology_config import *
from zephyr_ptm.ptm.application.configuration_handler import (
    FileConfigurationHandler)
from zephyr_ptm.ptm.ptm_constants import APPLICATION_START_TIMEOUT


class Zookeeper(application.Application):
    @staticmethod
    def get_name():
        return 'zookeeper'

    @staticmethod
    def get_type():
        return application.APPLICATION_TYPE_NSDB

    def __init__(self, host, app_id=''):
        super(Zookeeper, self).__init__(host, app_id)
        self.zookeeper_ips = []
        self.num_id = '1'
        self.ip = IP('', '')
        self.pid = 0
        self.configurator = ZookeeperFileConfiguration()
        self.snapshot_file = None

    def get_resource(self, resource_name, **kwargs):
        """
        Resource Type | Return Type
        --------------+--------------------------------
        log           | log file as a STRING
        """
        if resource_name == 'log':
            # TODO(micucci) Use an SSH accessor here if this app is
            # on a remote host
            floc = FileLocation(
                '/var/log/zookeeper.' + self.num_id + '/zookeeper.log')
            return floc.fetch_file()
        return None

    def configure(self, host_cfg, app_cfg):
        """
        Configure this host type from a PTC HostDef config and the
        app-specific configuration
        :type host_cfg: HostDef
        :type app_cfg: ApplicationDef
        :return:
        """
        if (len(host_cfg.interfaces.values()) > 0 and
                len(host_cfg.interfaces.values()[0].ip_addresses) > 0):
            self.ip = host_cfg.interfaces.values()[0].ip_addresses[0]

        if 'zookeeper_ips' in app_cfg.kwargs:
            for i in app_cfg.kwargs['zookeeper_ips']:
                self.zookeeper_ips.append(IP(i))

        if 'id' in app_cfg.kwargs:
            self.num_id = app_cfg.kwargs['id']

        if 'snapshot_file' in app_cfg.kwargs:
            self.snapshot_file = app_cfg.kwargs['snapshot_file']

        log_dir = '/var/log/zookeeper.' + self.num_id
        self.host.log_manager.add_external_log_file(
            FileLocation(log_dir + '/zookeeper.log'), self.num_id,
            '%Y-%m-%d %H:%M:%S,%f')

    def create_cfg_map(self):
        return {'num_id': self.num_id, 'ip': self.ip.to_map()}

    def config_app_for_process_control(self, cfg_map):
        self.num_id = cfg_map['num_id']
        self.ip = IP.from_map(cfg_map['ip'])

    def prepare_config(self, log_manager):
        self.configurator.configure(self.num_id, self.zookeeper_ips, self.LOG,
                                    snapshot_file=self.snapshot_file)

    def print_config(self, indent=0):
        super(Zookeeper, self).print_config(indent)
        print(('    ' * (indent + 1)) + 'Num-id: ' + self.num_id)
        print(('    ' * (indent + 1)) + 'Self-IP: ' + str(self.ip))
        print(('    ' * (indent + 1)) + 'Zookeeper-IPs: ' +
              ', '.join(str(ip) for ip in self.zookeeper_ips))

    # TODO(micucci): Add a wait_for_process_stop here (and to all hosts)
    def wait_for_process_start(self):
        # Checking Zookeeper status
        retries = 0
        max_retries = APPLICATION_START_TIMEOUT
        connected = False
        while not connected:
            ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.LOG.info('Trying to contact ZK server @' + self.ip.ip)
            try:
                ping_socket.settimeout(1)
                ping_socket.connect((self.ip.ip, 2181))
                ping_socket.send('ruok')
                if ping_socket.recv(16) == 'imok':
                    connected = True
            except IOError:
                pass
            finally:
                if not connected:
                    retries += 1
                    if retries > max_retries:
                        raise exceptions.SubprocessFailedException(
                            'Zookeeper host ' + self.num_id +
                            ' timed out while starting')
                    time.sleep(1)

        # TODO(micucci): Look into why this works everywhere BUT Jenkins gates
        """
        retries = 0
        while not LinuxCLI().exists('/run/zookeeper.' +
                                    str(self.num_id) + '/pid'):
            if retries > max_retries:
                raise SubprocessFailedException(
                    'Zookeeper PID file not created within timeout')
            time.sleep(1)
            retries += 1
        """

    def prepare_environment(self):
        self.configurator.mount_config(self.num_id)

    def cleanup_environment(self):
        self.configurator.unmount_config()

    def control_start(self):
        self.cli.rm_files('/var/log/zookeeper')
        process = self.cli.cmd_pipe(
            [['java',
              '-cp',
              '/etc/zookeeper/conf:'
              '/usr/share/java/jline.jar:'
              '/usr/share/java/log4j-1.2.jar:'
              '/usr/share/java/xercesImpl.jar:'
              '/usr/share/java/xmlParserAPIs.jar:'
              '/usr/share/java/netty.jar:'
              '/usr/share/java/slf4j-api.jar:'
              '/usr/share/java/slf4j-log4j12.jar:'
              '/usr/share/java/zookeeper.jar',
              '-Dcom.sun.management.jmxremote',
              '-Dcom.sun.management.jmxremote.local.only=false',
              '-Dzookeeper.log.dir=/var/log/zookeeper',
              '-Dzookeeper.root.logger=INFO,ROLLINGFILE',
              'org.apache.zookeeper.server.quorum.QuorumPeerMain',
              '/etc/zookeeper/conf/zoo.cfg']], blocking=False)

        print(process.stderr)

        if process.process.pid == -1:
            raise exceptions.SubprocessFailedException('java-zookeeper')

        real_pid = self.cli.get_parent_pids(process.process.pid)[-1]
        self.cli.write_to_file('/run/zookeeper/pid', str(real_pid))

    def control_stop(self):
        if self.cli.exists('/run/zookeeper/pid'):
            pid = self.cli.read_from_file('/run/zookeeper/pid')
            self.cli.cmd('kill ' + str(pid))
            self.cli.rm('/run/zookeeper/pid')


class ZookeeperFileConfiguration(FileConfigurationHandler):
    def __init__(self):
        super(ZookeeperFileConfiguration, self).__init__()

    def configure(self, num_id, zookeeper_ips, log, snapshot_file=None):
        if num_id == '1':
            etc_dir = '/etc/zookeeper.test'
            self.cli.rm(etc_dir)
            self.cli.copy_dir('/etc/zookeeper', etc_dir)

            write_string = ''
            for j in range(0, len(zookeeper_ips)):
                write_string += ('server.' + str(j + 1) + '=' +
                                 zookeeper_ips[j].ip + ':2888:3888\n')

            log.debug('write_str=' + write_string)
            self.cli.write_to_file(etc_dir + '/conf/zoo.cfg', write_string,
                                   append=True)

        var_lib_dir = '/var/lib/zookeeper.' + num_id
        var_log_dir = '/var/log/zookeeper.' + num_id
        var_run_dir = '/run/zookeeper.' + num_id

        self.cli.rm(var_lib_dir)
        self.cli.mkdir(var_lib_dir + '/data')

        if snapshot_file:
            tar_cli = cli.LinuxCLI(log_cmd=True,
                                   print_cmd_out=True,
                                   logger=log)
            cmd_out = tar_cli.cmd(
                'tar xvfz ' + snapshot_file + ' -C ' + var_lib_dir)
            if cmd_out.ret_code != 0:
                raise exceptions.SubprocessFailedException(
                    "extract of zk data failed: " + cmd_out.stdout +
                    '/' + cmd_out.stderr)

        self.cli.write_to_file(var_lib_dir + '/data/myid', num_id, False)
        self.cli.write_to_file(var_lib_dir + '/myid', num_id, False)
        self.cli.chown(var_lib_dir, 'zookeeper', 'zookeeper')

        self.cli.rm(var_log_dir)
        self.cli.mkdir(var_log_dir)
        self.cli.chown(var_log_dir, 'zookeeper', 'zookeeper')

        self.cli.mkdir('/run/zookeeper')
        self.cli.rm(var_run_dir)
        self.cli.mkdir(var_run_dir)
        self.cli.chown(var_run_dir, 'zookeeper', 'zookeeper')

    def mount_config(self, num_id):
        self.cli.mount('/run/zookeeper.' + num_id, '/run/zookeeper')
        self.cli.mount('/var/lib/zookeeper.' + num_id, '/var/lib/zookeeper')
        self.cli.mount('/var/log/zookeeper.' + num_id, '/var/log/zookeeper')
        self.cli.mount('/etc/zookeeper.test', '/etc/zookeeper')

    def unmount_config(self):
        self.cli.unmount('/run/zookeeper')
        self.cli.unmount('/var/lib/zookeeper')
        self.cli.unmount('/var/log/zookeeper')
        self.cli.unmount('/etc/zookeeper')
