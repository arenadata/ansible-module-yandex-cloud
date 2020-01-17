#!/usr/bin/python

# Copyright: (c) 2020, Rotaru Sergey <rsv@arenadata.io>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: ycc_vm
short_description: Ansible module to manage (create/update/delete) virtial machines in Yandex compute cloud
version_added: "2.4"
description:
    - "Ansible module to manage (create/update/delete) virtial machines in Yandex compute cloud"

options:
    name:
        description:
            - virtual machine name - must be unique throw all folders of cloud
        required: true
    folder_id:
        description:
            - virtual machine target folder id.
        required: true
    login:
        description:
            - user to create on virtual machine, required for linux instances
        required: false
    public_ssh_key:
        description:
            - created user`s openssh public key
        required: false
    password:
        description:
            - system administrator password, required for windows instances
        required: false
    hostname:
        description:
            - virtual machine hostname, default same as name
        required: false
    zone_id:
        description:
            - availability zone id. Default ru-central1-a
        required: false
    platform_id:
        description:
            - Default Intel Broadwell.
        required: false
    core_fraction:
        description:
            - Guaranteed vCPU share, default 100%
        required: false
    cores:
        description:
            - vCPU number, default 2.
        required: false
    memory:
        description:
            - RAM size, default 2 GB.
        required: false
    image_id:
        description:
            - boot image id.
        required: true
    disk_type:
        description:
            - primary disk type, default hdd
        required: false
    disk_size:
        description:
            - primary disk size in GB, default 10GB. 
        required: false
    secondary_disks_spec:
        description:
            - additional disk configuration spec.
        required: false
    subnet_id:
        description:
            - network id.
        required: required
    assign_public_ip:
        description:
            - assign public address, default false.
        required: false
    preemptible:
        description:
            - create preemtible(may be stopped after working 24h a row) vm.
        required: false
    metadata:
        description:
            - metadata to be translate to vm.
        required: false
    state:
        description:
            - present or absent. Default present.
        required: false
    operation:
        description:
            - stop, start or get_info. Mutually exclusive with state parameter.
        required: false

author:
    - Rotaru Sergey (rsv@arenadata.io)
'''


EXAMPLES = '''
- name: Create vm
  ycc_vm:
    name: my_vm
    login: john_doe
    public_ssh_key: john_doe_public_key
    hostname: my_vm
    zone_id: ru-central1-a
    folder_id: b1gotqhf076hh183dn
    platform_id: "Intel Cascade Lake"
    core_fraction: 100
    cores: 2
    memory: 2
    image_id: fd84uob96bu79jk8fqht
    disk_type: nvme
    disk_size: 50
    secondary_disks_spec:
        - autodelete: true
          description: disk1
          type: nvme
          size: 10
        - autodelete: false
          description: disk2
          type: hdd
          size: 100
    subnet_id: b0cccg656k0nixi92a
    assign_public_ip: false
    preemptible: true
    metadata:
        user-data:
    state: present
    
- name: Stop vm
  ycc_vm:
    name: my_tyni_vm
    operation: stop

- name: Start vm
  ycc_vm:
    name: my_tyni_vm
    operation: start

'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the test module generates
    type: str
    returned: always
'''

VMS_STATES = ['present', 'absent', 'update']
VMS_OPERATIONS = ['start', 'stop', 'get_info']
ZONE_IDS = ['ru-central1-a', 'ru-central1-b', 'ru-central1-c']
PLATFORM_IDS = ['Intel Cascade Lake', 'Intel Broadwell']  # standard-v1, standard-v2
CORE_FRACTIONS = [5, 20, 50, 100]
DISK_TYPES = ['hdd', 'nvme'] # network-nvme, network-hdd

from enum import Enum

from ansible.module_utils.yc import YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.compute.v1.instance_pb2 import (IPV4, Instance,
                                                  SchedulingPolicy)
from yandex.cloud.compute.v1.instance_service_pb2 import (
    AttachedDiskSpec, CreateInstanceMetadata, CreateInstanceRequest,
    NetworkInterfaceSpec, OneToOneNatSpec, PrimaryAddressSpec, ResourcesSpec)
from yandex.cloud.compute.v1.instance_service_pb2_grpc import \
    InstanceServiceStub


def vm_argument_spec():
    return dict(
        name=dict(type='str', required=True),
        folder_id=dict(type='str', required=True),
        login=dict(type='str', required=False),
        public_ssh_key=dict(type='str', required=False),
        hostname=dict(type='str', required=False),
        zone_id=dict(type='str', choices=ZONE_IDS, required=False),
        platform_id=dict(type='str', choices=PLATFORM_IDS, required=False),
        core_fraction=dict(type='int', choices=CORE_FRACTIONS, required=False),
        cores=dict(type='int', required=False, default=2),
        memory=dict(type='int', required=False, default=2),
        image_id=dict(type='str', required=True),
        disk_type=dict(choices=DISK_TYPES, required=False),
        disk_size=dict(type='int', required=False, default=10),
        secondary_disks_spec=dict(type='list', required=False),
        subnet_id=dict(type='int', required=False),
        assign_public_ip=dict(type='bool', required=False, default=False),
        preemptible=dict(type='bool', required=False, default=False),
        metadata=dict(type='dict', required=False),
        state=dict(choices=VMS_STATES, required=False),
        operation=dict(choices=VMS_OPERATIONS, required=False))

MUTUALLY_EXCLUSIVE = [['state', 'operation']]

class YccVM(YC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def manage_states(self):
        state = self.params.get('state')
        if state == "present":
            return self.add_vm()

        if state == "absent":
            return self.delete_vm()

        if state == "update":
            return self.update_vm()

    def manage_operations(self):
        operation = self.params.get('operation')

        if operation == "start":
            return self.start_vm()

        if operation == "stop":
            return self.stop_vm()

        if operation == "get_info":
            return self.get_info()

    def add_vm(self):
        name = self.params.get('name')
        folder_id = self.params.get('folder_id')
        login = self.params.get('login')
        hostname = self.params.get('hostname')
        public_ssh_key = self.params.get('public_ssh_key')
        zone_id = self.params.get('zone_id')
        platform_id = self.params.get('platform_id')
        core_fraction = self.params.get('core_fraction')
        cores = self.params.get('cores')
        memory = self.params.get('memory')
        image_id = self.params.get('image_id')
        disk_type = self.params.get('disk_type')
        disk_size = self.params.get('disk_size')
        secondary_disks_spec = self.params.get('secondary_disks_spec')
        subnet_id = self.params.get('subnet_id')
        assign_public_ip = self.params.get('assign_public_ip')
        preemptible = self.params.get('preemptible')
        metadata = self.params.get('metadata')

        instance_service = self.sdk.client(InstanceServiceStub)

        params=dict(
            folder_id=folder_id,
            name=name,
            resources_spec=ResourcesSpec(
                memory=memory * 2**30,
                cores=cores,
                core_fraction=core_fraction),
            zone_id=zone_id,
            platform_id=getattr(Platform_id, ''.join(platform_id.split())).value,
            boot_disk_spec=AttachedDiskSpec(
                auto_delete=True,
                disk_spec=AttachedDiskSpec.DiskSpec(
                    type_id=getattr(Disk_type, disk_type.upper()).value,
                    size=disk_size * 2 ** 30,
                    image_id=image_id)),
            network_interface_specs=[
                NetworkInterfaceSpec(
                    subnet_id=subnet_id)
            ],
        )

        if hostname:
            params['hostname'] = hostname
        if preemptible:
            params['scheduling_policy'] = SchedulingPolicy(preemptible=preemptible)
        if secondary_disks_spec:
            pass
        if assign_public_ip:
            params['network_interface_specs'][0].primary_v4_address_spec.CopyFrom(PrimaryAddressSpec(  # pylint: disable=no-member
                one_to_one_nat_spec=OneToOneNatSpec(
                    ip_version=IPV4
                )))
        if metadata:
            params['metadata'] = metadata

        if login and public_ssh_key:
            params['metadata'] = {"user-data": """
            #cloud-config
            datasource: { Ec2: { strict_id: false, ssh_pwauth: "no" } }
            users: [{ name: "%s", sudo: "ALL=(ALL) NOPASSWD:ALL", shell: "/bin/bash", ssh-authorized-keys: ["%s"] }]
            """ % (login, public_ssh_key)}

        operation = instance_service.Create(CreateInstanceRequest(**params))
        responce = self.sdk.waiter(operation.id).operation.response
        responce['json'] = MessageToDict(responce)
        return responce

    def delete_vm(self):
        pass

    def update_vm(self):
        pass

    def start_vm(self):
        pass

    def stop_vm(self):
        pass

    def get_info(self):
        pass

class Platform_id(Enum):
    IntelBroadwell = 'standard-v1'  
    IntelCascadeLake = 'standard-v2'

class Disk_type(Enum):
    HDD = 'network-hdd'
    NVME = 'network-nvme'


def main():
    argument_spec=vm_argument_spec()
    result = dict(
        changed=False,
        original_message='',
        message=''
    )
    module = YccVM(
        argument_spec=argument_spec,
        mutually_exclusive=MUTUALLY_EXCLUSIVE,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)

    try:
        if module.params.get('state'):
            response = module.manage_states()
        elif module.params.get('operation'):
            response = module.manage_operations()
        else:
            raise Exception('One of the state/operation should be provided.')

    except Exception as error:
        response['msg'] = error
        module.fail_json(**response)

    module.exit_json(**response)


if __name__ == '__main__':
    main()
