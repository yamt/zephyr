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
from CBT.installers.ComponentInstaller import ComponentInstaller
import CBT.VersionConfig as version_config


class MidonetComponentInstaller(ComponentInstaller):
    def create_repo_file(self, repo_obj, scheme, repo, username=None, password=None,
                         version=None, distribution='stable'):
        repo_name = repo + '-'
        if version is None or version == 'nightly':
            repo_name += 'nightly'
        else:
            repo_name += version_config.ConfigMap.get_configured_parameter('package_repo_version', version=version)
        repo_name += '-' + repo_obj.get_type()
        repo_obj.create_repo_file('midokura.midonet', scheme, repo_name, username, password, distribution)

    def get_pkg_list(self):
        config_map = version_config.ConfigMap.get_config_map()
        """ :type: dict [str, str]"""
        major_version = config_map["master_major_version"] \
            if (self.version == 'nightly' or self.version is None) \
            else self.version.major

        if major_version not in config_map:
            raise ArgMismatchException("Major version not found in config map: " + major_version)
        package_list = config_map[major_version]["installed_packages"]
        return package_list

    def install_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.install_packages(self.get_pkg_list(), exact_version)

    def uninstall_packages(self, repo, exact_version=None):
        """
        :type repo: PackageRepo
        :type exact_version: str
        :return:
        """
        repo.uninstall_packages(self.get_pkg_list(), exact_version)