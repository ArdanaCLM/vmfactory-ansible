#!/usr/bin/env python
#
# An Ansible module to return list of virtual objects (vm, networks)
# that "belong" to Ardana OpenStack
#
# (c) Copyright 2016 Hewlett Packard Enterprise Development LP
# (c) Copyright 2017 SUSE LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import xml.etree.ElementTree as etree
import libvirt


ARDANA_NS = "ardana_openstack"


DOCUMENTATION = '''
---
module: list_ardana_virt_objects
short_decription: Check for ardana vms and virtual networks
list_vms: True, list ardana vms by name
list_nets: True, list ardana virtual networks by name
uri: qemu:///system, URI of hypervisor to connect to.
'''


class ArdanaMetadataError(Exception):
    pass


class process_xml(object):
    def __init__(self, obj_xml):
        self._xmlreader = etree.fromstring(obj_xml)

    def tostr(self, node):

        if isinstance(node, etree._Element):
            if len(node.getchildren()) == 0:
                return node.text
            return etree.tostring(node)
        return str(node)

    def read_xml(self, xpath=None, dflt=None):

        try:
            nodes = self._xmlreader.findall(xpath)
            values = [self.tostr(node) for node in nodes]
            return values

        except Exception, e:
            raise ArdanaMetadataError("xml: %s" % str(e))

        return dflt

    _ardana_prefix = "ardana-"

    @property
    def is_ardana(self):
        # Libvirt, prior to V2.1.0, doesn't maintain a metadata node
        # for network objects so can only check for the ardana- prefix
        return (bool(self.read_xml(xpath="./metadata/%s" % ARDANA_NS)) or
                (self._xmlreader.tag == "network" and
                 self.name.startswith(self._ardana_prefix)))

    @property
    def name(self):
        return self.read_xml(xpath="./name")[0]


class list_ardana_virt_objects(object):

    def __init__(self, uri=None):
        conn = libvirt.openReadOnly(uri)
        if not conn:
            raise Exception("hypervisor connection failure")

        self._conn = conn

    @property
    def _vms(self):
        return self._conn.listAllDomains()

    @property
    def _nets(self):
        return self._conn.listAllNetworks()

    @staticmethod
    def _list_ardana_objs(objs):
        xmls = [process_xml(o.XMLDesc(0)) for o in objs]
        return [x.name for x in xmls if x.is_ardana]

    @property
    def ardana_vms(self):
        return self._list_ardana_objs(self._vms)

    @property
    def ardana_nets(self):
        return self._list_ardana_objs(self._nets)


def main():
    module = AnsibleModule(  # noqa
        argument_spec=dict(
            list_vms=dict(type='bool'),
            list_nets=dict(type='bool'),
            uri=dict(default='qemu:///system')
        ),
        supports_check_mode=False
    )

    try:
        params = module.params
        processor = list_ardana_virt_objects(params['uri'])
        result = {}
        if params['list_vms']:
            result['ardana_vm_names'] = processor.ardana_vms

        if params['list_nets']:
            result['ardana_net_names'] = processor.ardana_nets

        module.exit_json(**(result))

    except Exception, e:
        module.fail_json(msg='Exception: %s' % e)


from ansible.module_utils.basic import *  # noqa
if __name__ == "__main__":
    main()
