#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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

VMS_STATES = ['present', 'absent', ]
VMS_OPERATIONS = ['start', 'stop', 'get_info', 'update']
ZONE_IDS = ['ru-central1-a', 'ru-central1-b', 'ru-central1-c']
PLATFORM_IDS = ['Intel Cascade Lake', 'Intel Broadwell']
CORE_FRACTIONS = [5, 20, 50, 100]
DISK_TYPES = ['hdd', 'nvme']

from copy import deepcopy
from enum import Enum
from json import dumps

from ansible.module_utils.yc import YC
from google.protobuf.json_format import MessageToDict
from yandex.cloud.compute.v1.disk_service_pb2 import GetDiskRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub
from yandex.cloud.compute.v1.instance_pb2 import IPV4, SchedulingPolicy
from yandex.cloud.compute.v1.instance_service_pb2 import (
    AttachedDiskSpec, CreateInstanceRequest, DeleteInstanceRequest,
    ListInstancesRequest, NetworkInterfaceSpec, OneToOneNatSpec,
    PrimaryAddressSpec, ResourcesSpec, StartInstanceRequest,
    StopInstanceRequest)
from yandex.cloud.compute.v1.instance_service_pb2_grpc import \
    InstanceServiceStub


def vm_argument_spec():
    return dict(
        name=dict(type='str', required=True),
        folder_id=dict(type='str', required=True),
        login=dict(type='str', required=False),
        public_ssh_key=dict(type='str', required=False),
        hostname=dict(type='str', required=False),
        zone_id=dict(type='str', choices=ZONE_IDS, required=False, default='ru-central1-a'),
        platform_id=dict(type='str', choices=PLATFORM_IDS,
                         required=False, default='Intel Broadwell'),
        core_fraction=dict(type='int', choices=CORE_FRACTIONS, required=False, default=100),
        cores=dict(type='int', required=False, default=2),
        memory=dict(type='int', required=False, default=2),
        image_id=dict(type='str', required=False),
        disk_type=dict(choices=DISK_TYPES, required=False, default='hdd'),
        disk_size=dict(type='int', required=False, default=10),
        secondary_disks_spec=dict(type='list', required=False),
        subnet_id=dict(type='str', required=False),
        assign_public_ip=dict(type='bool', required=False, default=False),
        preemptible=dict(type='bool', required=False, default=False),
        metadata=dict(type='dict', required=False),
        state=dict(choices=VMS_STATES, required=False),
        operation=dict(choices=VMS_OPERATIONS, required=False))

MUTUALLY_EXCLUSIVE = [['state', 'operation'],
                      ['login', 'metadata'],
                      ['metadata', 'public_ssh_key']]
REQUIRED_TOGETHER = [['login', 'public_ssh_key']]
REQUIRED_IF = [['state', 'present', ['image_id', 'subnet_id']]]

class YccVM(YC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_service = self.sdk.client(InstanceServiceStub)
        self.disk_service = self.sdk.client(DiskServiceStub)

    def _list_by_name(self, name, folder_id):
        instances = self.instance_service.List(ListInstancesRequest(
            folder_id=folder_id,
            filter='name="%s"' % name
        ))
        return MessageToDict(instances)

    def _get_instance(self, name, folder_id):
        instance = self._list_by_name(name, folder_id)
        if instance:
            return instance['instances'][0]
        return instance

    def _compare_disk(self, disk_id, disk_spec):
        err = list()
        disk = MessageToDict(self.disk_service.Get(GetDiskRequest(
            disk_id=disk_id)))
        if getattr(DiskType, disk_spec['disk_type'].upper()).value == disk['typeId']:
            err.append('disk_type')

        if disk_spec['disk_size'] * 2**30 == disk['size']:
            err.append('disk_size')

        if disk_spec.get('image_id') and disk_spec['image_id'] == disk['sourceImageId']:
            err.append('image_id')

        return err

    def _is_same(self, instance: dict, spec: dict):
        err = list()

        err.extend(
            [k for k, v in spec.items()
             if k in ['folder_id', 'name', 'zone_id', 'platform_id', 'hostname']
             and not instance[_camel(k)] == v])
        err.extend(
            [k for k, v in spec.items()
             if k in ['memory', 'cores', 'core_fraction']
             and not instance['resources'][_camel(k)] == v])
        if instance['networkInterfaces'][0]['subnetId'] == spec['subnetId']:
            err.append('subnet_id')
        if instance.get('schedulingPolicy', {}).get('preemptible') == spec['preemptible']:
            err.append('preemptible')

        err.extend(self._compare_disk(instance['bootDisk']['diskId'], spec))

        for idx, disk in enumerate(instance['secondaryDisks']):
            fault_keys=list()
            if spec['secondary_disks_spec'][idx].get('autodelete', True) != disk['autoDelete']:
                fault_keys.append('autodelete')
            fault_keys.extend(self._compare_disk(disk['diskId'],
                                                 spec['secondary_disks_spec'][idx]))
            if fault_keys:
                err.append(dumps({'param_key': 'secondary_disks_spec',
                                  'index:': idx,
                                  'fault_keys': fault_keys
                                  }))

        return err

    def _get_instance_params(self):
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

        params = dict(
            folder_id=folder_id,
            name=name,
            resources_spec=_get_resource_spec(memory, cores, core_fraction),
            zone_id=zone_id,
            platform_id=_get_platform_id(platform_id),
            boot_disk_spec=_get_attached_disk_spec(disk_type, disk_size, image_id),
            network_interface_specs=_get_network_interface_spec(subnet_id, assign_public_ip)
        )

        if secondary_disks_spec and secondary_disks_spec[0]:
            params['secondary_disk_specs'] = _get_secondary_disk_specs(secondary_disks_spec)
        if hostname:
            params['hostname'] = hostname
        if preemptible:
            params['scheduling_policy'] = _get_scheduling_policy(preemptible)
        if metadata:
            params['metadata'] = metadata

        if login and public_ssh_key:
            params['metadata'] = {
                "user-data": ("#cloud-config\n"
                              "datasource: { Ec2: { strict_id: false, ssh_pwauth: \"no\" } }\n"
                              "users: [{\n"
                              "   name: \"%s\",\n"
                              "   sudo: \"ALL=(ALL) NOPASSWD:ALL\",\n"
                              "   shell: \"/bin/bash\",\n"
                              "   ssh-authorized-keys: [\"%s\"]\n"
                              "}]") % (login, public_ssh_key)}
        return params

    def manage_states(self):
        state = self.params.get('state')
        if state == "present":
            return self.add_vm()

        if state == "absent":
            return self.delete_vm()

    def manage_operations(self):
        operation = self.params.get('operation')

        if operation == "start":
            return self.start_vm()

        if operation == "stop":
            return self.stop_vm()

        if operation == "get_info":
            return self.get_info()

        if operation == "update":
            return self.update_vm()

    def add_vm(self):
        spec = deepcopy(self.params)
        response = dict()
        response['changed'] = False
        name = self.params.get('name')
        folder_id = self.params.get('folder_id')

        instance = self._get_instance(name, folder_id)
        if instance:
            compare_result = self._is_same(instance, spec)
            if compare_result:
                response['failed'] = True
                response['msg'] = "Instance already exits and %s"\
                                  " request params are different" % ', '.join(compare_result)
        else:
            params = self._get_instance_params()

            operation = self.instance_service.Create(CreateInstanceRequest(**params))
            cloud_response = self.waiter(operation)

            response['response'] = MessageToDict(
                cloud_response)
            response['changed'] = True
        return response

    def delete_vm(self):
        response = dict()
        response['changed'] = False
        name = self.params.get('name')
        folder_id = self.params.get('folder_id')
        instance = self._get_instance(name, folder_id)
        if instance:
            operation = self.instance_service.Delete(DeleteInstanceRequest(
                instance_id=instance['id']
            ))
            cloud_response = self.waiter(operation)

            response['response'] = MessageToDict(
                cloud_response)
            response['changed'] = True
        return response

    def update_vm(self):
        pass

    def start_vm(self):
        response = dict()
        response['changed'] = False
        folder_id = self.params.get('folder_id')
        name = self.params.get('name')
        instance = self._get_instance(name, folder_id)
        if instance:
            if instance['status'] == 'STOPPED':
                operation = self.instance_service.Start(StartInstanceRequest(
                    instance_id=instance['id']
                ))
                cloud_response = self.waiter(operation)

                response['response'] = MessageToDict(
                    cloud_response)
                response['changed'] = True
            elif instance['status'] != 'RUNNING':
                response['failed'] = True
                response['msg'] = 'Current instance status(%s) doens`t allow start action' % instance['status']
        else:
            response['failed'] = True
            response['msg'] = 'Instance with such name(%s) doesn`t exist' % name

        return response

    def stop_vm(self):
        response = dict()
        response['changed'] = False
        folder_id = self.params.get('folder_id')
        name = self.params.get('name')
        instance = self._get_instance(name, folder_id)
        if instance:
            if instance['status'] == 'RUNNING':
                operation = self.instance_service.Stop(StopInstanceRequest(
                    instance_id=instance['id']
                ))
                cloud_response = self.waiter(operation)

                response['response'] = MessageToDict(
                    cloud_response)
                response['changed'] = True
            elif instance['status'] != 'STOPPED':
                response['failed'] = True
                response['msg'] = 'Current instance status(%s) doens`t allow start action' % instance['status']
        else:
            response['failed'] = True
            response['msg'] = 'Instance with such name(%s) doesn`t exist' % name

        return response

    def get_info(self):
        response = dict()
        name = self.params.get('name')
        folder_id = self.params.get('folder_id')
        instance = self._get_instance(name, folder_id)
        if instance:
            response['instance'] = instance
        else:
            response['msg'] = 'No instance found'

        return response


class PlatformId(Enum):
    IntelBroadwell = 'standard-v1'
    IntelCascadeLake = 'standard-v2'


class DiskType(Enum):
    HDD = 'network-hdd'
    NVME = 'network-nvme'


def _camel(snake_case):
    first, *others = snake_case.split('_')
    return ''.join([first.lower(), *map(str.title, others)])


def _get_attached_disk_spec(disk_type, disk_size, image_id):
    return AttachedDiskSpec(
        auto_delete=True,
        disk_spec=AttachedDiskSpec.DiskSpec(
            type_id=getattr(DiskType, disk_type.upper()).value,
            size=disk_size * 2 ** 30,
            image_id=image_id))

def _get_secondary_disk_specs(secondary_disks):
    return list(map(
        lambda disk: AttachedDiskSpec(    
            auto_delete=disk.get('autodelete', True),
            disk_spec=AttachedDiskSpec.DiskSpec(
                description=disk.get('description'),
                type_id=getattr(DiskType, secondary_disks['disk_type'].upper()).value,
                size=secondary_disks['disk_size'] * 2 ** 30
                )
        ),
        secondary_disks))

def _get_resource_spec(memory, cores, core_fraction):
    return ResourcesSpec(
        memory=memory * 2**30,
        cores=cores,
        core_fraction=core_fraction)


def _get_platform_id(platform_id):
    return getattr(PlatformId, ''.join(platform_id.split())).value


def _get_network_interface_spec(subnet_id, assign_public_ip):
    net_spec = [
        NetworkInterfaceSpec(
            subnet_id=subnet_id,
            primary_v4_address_spec=PrimaryAddressSpec())]
    if assign_public_ip:
        net_spec[0].primary_v4_address_spec.one_to_one_nat_spec.CopyFrom(  # pylint: disable=no-member
            OneToOneNatSpec(
                ip_version=IPV4
            ))
    return net_spec


def _get_scheduling_policy(preemptible):
    return SchedulingPolicy(preemptible=preemptible)


def main():
    argument_spec = vm_argument_spec()
    result = dict(
        changed=False,
        original_message='',
        message=''
    )
    module = YccVM(
        argument_spec=argument_spec,
        mutually_exclusive=MUTUALLY_EXCLUSIVE,
        required_together=REQUIRED_TOGETHER,
        required_if=REQUIRED_IF
    )
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

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
