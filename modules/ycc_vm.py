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
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: ycc_vm
short_description: Ansible module to manage (create/update/delete) virtial machines in Yandex compute cloud
version_added: "2.4"
description:
    - "Ansible module to manage (create/update/delete) virtial machines in Yandex compute cloud"

options:
    token:
        description:
            - Oauth token to access cloud.
        type: str
        required: true
    name:
        description:
            - Virtual machine name - must be unique throw all folders of cloud.
        type: str
        required: true
    folder_id:
        description:
            - Virtual machine target folder id.
        type: str
        required: true
    login:
        description:
            - User to create on virtual machine, required for linux instances.
            - Required together with I(public_ssh_key).
            - Required with I(state=present), mutually exclusive with I(metadata).
        type: str
        required: false
    public_ssh_key:
        description:
            - Created user`s openssh public key.
            - Required together with I(public_ssh_key).
            - Required with I(state=present), mutually exclusive with I(metadata).
        type: str
        required: false
    # password:
    #     description:
    #         - System administrator password, required for windows instances.
    #     required: false
    hostname:
        description:
            - Virtual machine hostname, default same as name.
        type: str
        required: false
    zone_id:
        description:
            - Availability zone id.
        type: str
        required: false
        default: ru-central1-a
        choises:
            - ru-central1-a
            - ru-central1-b
            - ru-central1-c
    active_operations_limit_timeout:
        type: integer
        description: "Active operations limit timeout in seconds"
        display_name: "Active operations limit timeout"
    platform_id:
        description:
            - Platform id.
        default: Intel Broadwell.
        type: str
        required: false
        choises:
            - Intel Cascade Lake
            - Intel Broadwell
    core_fraction:
        description:
            - Guaranteed vCPU share
        type: int
        default: 100
        required: false
        choises:
            - 5
            - 20
            - 50
            - 100
    cores:
        description:
            - vCPU number.
        type: int
        default: 2
        required: false
    memory:
        description:
            - RAM size, GB.
        type: int
        default: 2
        required: false
    image_family:
        description:
            - Boot image disk family.
            - Will be used latest image from family to create boot disk.
            - Required with I(state=present), mutually exclusive with I(image_id)
        type: str
        required: false
    image_id:
        description:
            - Boot image id.
            - Required with I(state=present).
            - Required with I(state=present), mutually exclusive with I(image_family)
        type: str
        required: false
    disk_type:
        description:
            - Primary disk type.
        default: hdd
        type: str
        required: false
        choises:
            - hdd
            - nvme
    disk_size:
        description:
            - Primary disk size in GB.
        type: int
        default: 10
        required: false
    secondary_disks_spec:
        description:
            - Additional disk configuration spec.
        type: list
        required: false
    subnet_id:
        description:
            - Network id.
            - Required with I(state=present)
        required: false
    assign_public_ip:
        description:
            - Assign public address.
        type: bool
        default: false
        required: false
    preemptible:
        description:
            - Create preemtible(may be stopped after working 24h a row) vm.
        type: bool
        default: false
        required: false
    metadata:
        description:
            - Metadata to be translate to vm.
        type: dict
        required: false
    labels:
        description:
            - Vm key value labels
        type: dict
        required: false
    state:
        description:
            - VM state.
            - Mutually exclusive with I(operation).
        choices:
            - present
            - absent
        type: str
        required: false
    operation:
        description:
            - stop, start or get_info.
            - Mutually exclusive with I(state).
        choises:
            - start
            - stop
            - get_info
            - update
        required: false
    max_retries:
        description:
            - Max retries to proceed operation/state.
        type: int
        default: 5
        required: false
    retry_multiplayer:
        description:
            - Retry multiplayer between retries to proceed operation/state
            - (wait retry_multiplayer*curent_retry seconds)
        type: int
        default: 2
        required: false

author:
    - Rotaru Sergey (rsv@arenadata.io)
"""


EXAMPLES = """
- name: Create vm
  ycc_vm:
    token: {{ my_token }}
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
        user-data: "cloud init format in str"
    labels:
        my_vm: 1
    state: present

- name: Stop vm
  ycc_vm:
    token: {{ my_token }}
    name: my_tyni_vm
    operation: stop

- name: Start vm
  ycc_vm:
    token: {{ my_token }}
    name: my_tyni_vm
    operation: start

"""

RETURN = """
original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the test module generates
    type: str
    returned: always
"""

VMS_STATES = ["present", "absent"]
VMS_OPERATIONS = ["start", "stop", "get_info", "update"]
PLATFORM_IDS = ["Intel Cascade Lake", "Intel Broadwell"]
CORE_FRACTIONS = [5, 20, 50, 100]
DISK_TYPES = ["hdd", "ssd"]

# pylint: disable=wrong-import-position
import datetime
import traceback
from copy import deepcopy
from enum import Enum
from json import dumps
from time import sleep

from ansible.module_utils.yc import (  # pylint: disable=E0611, E0401
    YC,
    ZONE_IDS,
    response_error_check,
)
from google.protobuf.field_mask_pb2 import FieldMask
from google.protobuf.json_format import MessageToDict
from grpc._channel import _InactiveRpcError
from yandex.cloud.compute.v1.disk_service_pb2 import GetDiskRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub
from yandex.cloud.compute.v1.image_service_pb2 import GetImageLatestByFamilyRequest
from yandex.cloud.compute.v1.image_service_pb2_grpc import ImageServiceStub
from yandex.cloud.compute.v1.instance_pb2 import IPV4, SchedulingPolicy
from yandex.cloud.compute.v1.instance_service_pb2 import (
    AttachedDiskSpec,
    CreateInstanceRequest,
    DeleteInstanceRequest,
    ListInstancesRequest,
    NetworkInterfaceSpec,
    OneToOneNatSpec,
    PrimaryAddressSpec,
    ResourcesSpec,
    StartInstanceRequest,
    StopInstanceRequest,
    UpdateInstanceRequest,
)
from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from yandex.cloud.compute.v1.snapshot_service_pb2 import GetSnapshotRequest
<<<<<<< HEAD
from grpc._channel import _InactiveRpcError
from google.protobuf.field_mask_pb2 import FieldMask
import datetime
from ansible.utils.display import Display
=======
from yandex.cloud.compute.v1.snapshot_service_pb2_grpc import SnapshotServiceStub
>>>>>>> 8dc242542ea8fb85278103da19f1b8e70fd7ea81


def vm_argument_spec():
    return dict(
        name=dict(type="str", required=True),
        folder_id=dict(type="str", required=True),
        login=dict(type="str", required=False),
        public_ssh_key=dict(type="str", required=False),
        hostname=dict(type="str", required=False),
        zone_id=dict(
            type="str", choices=ZONE_IDS, required=False, default="ru-central1-a"
        ),
        active_operations_limit_timeout=dict(type="int", required=False, default=None),
        platform_id=dict(
            type="str",
            choices=PLATFORM_IDS,
            required=False,
            default="Intel Cascade Lake",
        ),
        core_fraction=dict(
            type="int", choices=CORE_FRACTIONS, required=False, default=100
        ),
        cores=dict(type="int", required=False, default=2),
        memory=dict(type="int", required=False, default=2),
        image_family=dict(type="str", required=False),
        image_id=dict(type="str", required=False),
        snapshot_id=dict(type="str", required=False),
        disk_type=dict(choices=DISK_TYPES, required=False, default="hdd"),
        disk_size=dict(type="int", required=False, default=10),
        secondary_disks_spec=dict(type="list", required=False),
        subnet_id=dict(type="str", required=False),
        assign_public_ip=dict(type="bool", required=False, default=False),
        preemptible=dict(type="bool", required=False, default=False),
        metadata=dict(type="dict", required=False),
        labels=dict(type="dict", required=False),
        state=dict(choices=VMS_STATES, required=False),
        operation=dict(choices=VMS_OPERATIONS, required=False),
    )


MUTUALLY_EXCLUSIVE = (
    ("state", "operation"),
    ("login", "metadata"),
    ("metadata", "public_ssh_key"),
    ("image_id", "image_family"),
    ("snapshot_id", "image_id"),
    ("snapshot_id", "image_family"),
)
REQUIRED_TOGETHER = ("login", "public_ssh_key")

REQUIRED_IF = (
    ("state", "present", ("subnet_id",)),
    ("state", "present", ("image_id", "image_family", "snapshot_id"), True),
)


class YccVM(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance_service = self.sdk.client(InstanceServiceStub)
        self.disk_service = self.sdk.client(DiskServiceStub)
        self.image_service = self.sdk.client(ImageServiceStub)
        self.snapshot_service = self.sdk.client(SnapshotServiceStub)


    def active_op_limit_timeout(self, timeout, fn, *args, **kwargs):
        """This funtion solves action operation queue cloud behaviour
        Its purpose its to wait until queue will be ready to get new operations
        0 - wait infinite
        positive integer - wait seconds
        None - dont wait.
        """
        if timeout is None:
            op = fn(*args, **kwargs)
        else:
            start_time = datetime.datetime.now()
            retry = False
            while (
                timeout == 0 or (datetime.datetime.now() - start_time).seconds < timeout
            ):
                try:
                    op = fn(*args, **kwargs)
                    if retry:
                        self.warn(
                            (
                                f"{(datetime.datetime.now() - start_time).seconds}"
                                f" waited to create operation"
                            )
                        )
                    break
                except _InactiveRpcError as err:
                    if err._state.response.contains(  # pylint: disable=W0212
                        "The limit on maximum number of active operations has exceeded"
                    ):
                        sleep(5)
                        retry = True
            else:
                raise TimeoutError(
                    f"Cloud active operation timeout = {timeout} exceeded"
                )
        return op

    def _list_by_name(self, name, folder_id):
        instances = self.instance_service.List(
            ListInstancesRequest(folder_id=folder_id, filter='name="%s"' % name)
        )
        return MessageToDict(instances)

    def _get_instance(self, name, folder_id):
        valid_statuses = ("RUNNING", "STOPPED")
        timeout = 60
        step = 5
        timer = 0
        while timer < timeout:
            instance = self._list_by_name(name, folder_id)
            if not instance or (
                instance.get("instances", ({},))[0].get("status") in valid_statuses
            ):
                break
            if instance.get("instances", ({},))[0].get("status") == "ERROR":
                raise Exception("Instance status is ERROR")
            sleep(step)
            timer += step
        else:
            raise TimeoutError("Wait for instance status exceeded")
        return instance.get("instances", (None,))[0]

    def _compare_disk(self, disk_id, disk_spec):
        err = list()
        disk = MessageToDict(self.disk_service.Get(GetDiskRequest(disk_id=disk_id)))
        if disk_spec["type"] != disk["typeId"]:
            err.append("type")

        if str(disk_spec["size"]) != disk["size"]:
            err.append("size")

        if disk_spec.get("image_id") and disk_spec["image_id"] != disk["sourceImageId"]:
            err.append("image_id")

        return err

    def _is_same(self, instance: dict, spec: dict):
        err = list()

        err.extend(
            [
                k
                for k, v in spec.items()
                if k in ["folder_id", "name", "zone_id", "platform_id"]
                and not instance[_camel(k)] == v
            ]
        )

        labels = spec["labels"] if spec.get("labels") is not None else {}
        instance_labels = (
            instance["labels"] if instance.get("labels") is not None else {}
        )
        lables_key_set = set(labels.keys())
        instance_lables_key_set = set(instance_labels.keys())

        labels_diff = list(lables_key_set.difference(instance_lables_key_set))
        labels_intersect = list(
            filter(
                lambda x: labels[x] != instance_labels[x],
                lables_key_set.intersection(instance_lables_key_set),
            )
        )
        if labels_diff or labels_intersect:
            err.extend([{"labels": labels_diff + labels_intersect}])

        if instance["networkInterfaces"][0]["subnetId"] != spec["subnet_id"]:
            err.append("subnet_id")
        if (
            instance.get("schedulingPolicy", {}).get("preemptible", False)
            != spec["preemptible"]
        ):
            err.append("preemptible")

        # prepare boot_disk_spec
        boot_disk_spec = {
            "type": spec["disk_type"],
            "size": spec["disk_size"],
            "image_id": spec["image_id"],
        }
        err.extend(self._compare_disk(instance["bootDisk"]["diskId"], boot_disk_spec))

        if spec.get("secondary_disks_spec") and not instance.get("secondaryDisks"):
            err.extend("secondary_disk not presented on instance")
        elif not spec.get("secondary_disks_spec") and instance.get("secondaryDisks"):
            err.extend(
                "secondary_disk presented on instance but not described in module call"
            )
        elif spec.get("secondary_disks_spec") and instance.get("secondaryDisks"):
            for idx, disk in enumerate(instance["secondaryDisks"]):
                fault_keys = list()
                if (
                    spec["secondary_disks_spec"][idx].get("autodelete", True)
                    != disk["autoDelete"]
                ):
                    fault_keys.append("autodelete")
                fault_keys.extend(
                    self._compare_disk(
                        disk["diskId"], spec["secondary_disks_spec"][idx]
                    )
                )
                if fault_keys:
                    err.append(
                        dumps(
                            {
                                "param_key": "secondary_disks_spec",
                                "index:": idx,
                                "fault_keys": fault_keys,
                            }
                        )
                    )

        return err

    def _translate(self):
        """This funtion must convert all GB values to bytes as ycc api needs.
        Human readable disk type and platform id to api types.

        :param params: [description]
        :type params: [type]
        """
        params = deepcopy(self.params)
        for key in params:
            if key in ["memory", "disk_size"]:
                params[key] = params[key] * 2 ** 30
            elif key == "disk_type":
                params[key] = getattr(DiskType, params[key].upper()).value
            elif key == "platform_id":
                params[key] = getattr(PlatformId, params[key].replace(" ", "")).value
            elif key == "secondary_disks_spec" and params.get("secondary_disks_spec"):
                for disk in params[key]:
                    if "type" in disk:
                        disk["type"] = getattr(DiskType, disk["type"].upper()).value
                    if "size" in disk:
                        disk["size"] = disk["size"] * 2 ** 30

        if params.get("image_family"):
            params["image_id"] = self.image_service.GetLatestByFamily(
                GetImageLatestByFamilyRequest(
                    folder_id="standard-images", family=params.get("image_family")
                )
            ).id
        elif params.get("image_id") or params.get("snapshot_id"):
            pass
        else:
            raise NotImplementedError

        return params

    def _get_instance_params(self, spec):  # pylint: disable=R0914
        name = spec.get("name")
        folder_id = spec.get("folder_id")
        login = spec.get("login")
        hostname = spec.get("hostname") if spec.get("hostname") else spec.get("name")
        public_ssh_key = spec.get("public_ssh_key")
        zone_id = spec.get("zone_id")
        platform_id = spec.get("platform_id")
        core_fraction = spec.get("core_fraction")
        cores = spec.get("cores")
        memory = spec.get("memory")
        image_id = spec.get("image_id")
        snapshot_id = spec.get("snapshot_id")
        disk_type = spec.get("disk_type")
        disk_size = spec.get("disk_size")
        secondary_disks_spec = spec.get("secondary_disks_spec")
        subnet_id = spec.get("subnet_id")
        assign_public_ip = spec.get("assign_public_ip")
        preemptible = spec.get("preemptible")
        metadata = spec.get("metadata")
        labels = spec.get("labels")

        if snapshot_id:
            try:
                self.snapshot_service.Get(GetSnapshotRequest(snapshot_id=snapshot_id))
            except _InactiveRpcError as err:
                raise ValueError(f"Snapshot with id:{snapshot_id} not found") from err

        params = dict(
            folder_id=folder_id,
            name=name,
            resources_spec=_get_resource_spec(memory, cores, core_fraction),
            zone_id=zone_id,
            platform_id=platform_id,
            boot_disk_spec=_get_attached_disk_spec(
                disk_type, disk_size, snapshot_id=snapshot_id, image_id=image_id
            ),
            network_interface_specs=_get_network_interface_spec(
                subnet_id, assign_public_ip
            ),
        )

        if secondary_disks_spec and secondary_disks_spec[0]:
            params["secondary_disk_specs"] = _get_secondary_disk_specs(
                secondary_disks_spec
            )
        if hostname:
            params["hostname"] = hostname
        if preemptible:
            params["scheduling_policy"] = _get_scheduling_policy(preemptible)
        if metadata:
            params["metadata"] = metadata
        if labels:
            params["labels"] = labels

        if login and public_ssh_key:
            params["metadata"] = {
                "user-data": (
                    "#cloud-config\n"
                    'datasource: { Ec2: { strict_id: false, ssh_pwauth: "no" } }\n'
                    "users: [{\n"
                    '   name: "%s",\n'
                    '   sudo: "ALL=(ALL) NOPASSWD:ALL",\n'
                    '   shell: "/bin/bash",\n'
                    '   ssh-authorized-keys: ["%s"]\n'
                    "}]"
                )
                % (login, public_ssh_key)
            }
        return params

    def manage_states(self):
        sw = {
            "present": self.add_vm,
            "absent": self.delete_vm,
        }
        return sw[self.params.get("state")]()

    def manage_operations(self):
        sw = {
            "start": self.start_vm,
            "stop": self.stop_vm,
            "get_info": self.get_info,
            "update": self.update_vm,
        }
        return sw[self.params.get("operation")]()

    def add_vm(self):
        spec = self._translate()
        response = dict()
        response["changed"] = False
        name = self.params.get("name")
        folder_id = self.params.get("folder_id")
        instance = self._get_instance(name, folder_id)
        if instance:
            compare_result = self._is_same(instance, spec)
            if compare_result:
                response["failed"] = True
                response["msg"] = (
                    "Instance already exits and %s"
                    " request params are different" % ", ".join(compare_result)
                )
            else:
                response["response"] = instance
                response["failed"] = False
                response["changed"] = False
        else:
            params = self._get_instance_params(spec)
            operation = self.active_op_limit_timeout(
                self.params.get("active_operations_limit_timeout"),
                self.instance_service.Create,
                CreateInstanceRequest(**params),
            )
            cloud_response = self.waiter(operation)
            response.update(MessageToDict(cloud_response))
            response = response_error_check(response)
        return response

    def delete_vm(self):
        response = dict()
        response["changed"] = False
        name = self.params.get("name")
        folder_id = self.params.get("folder_id")
        instance = self._get_instance(name, folder_id)
        if instance:
            operation = self.active_op_limit_timeout(
                self.params.get("active_operations_limit_timeout"),
                self.instance_service.Delete,
                DeleteInstanceRequest(instance_id=instance["id"]),
            )
            cloud_response = self.waiter(operation)

            response["response"] = MessageToDict(cloud_response)
            response = response_error_check(response)
        return response

    def update_vm(self):
        response = dict()
        name = self.params.get("name")
        folder_id = self.params.get("folder_id")
        labels = self.params.get("labels")
        instance = self._get_instance(name, folder_id)
        protobuf_field_mask = FieldMask(paths=["labels"])
        if instance:
            operation = self.active_op_limit_timeout(
                self.params.get("active_operations_limit_timeout"),
                self.instance_service.Update,
                UpdateInstanceRequest(
                    instance_id=instance["id"],
                    labels=labels,
                    update_mask=protobuf_field_mask,
                ),
            )
            cloud_response = self.waiter(operation)
            response["response"] = MessageToDict(cloud_response)
            response = response_error_check(response)
        else:
            response["msg"] = "Update instance is missing"
            response = response_error_check(response)
        return response

    def start_vm(self):
        response = dict()
        response["changed"] = False
        folder_id = self.params.get("folder_id")
        name = self.params.get("name")
        instance = self._get_instance(name, folder_id)
        if instance:
            if instance["status"] == "STOPPED":
                operation = self.active_op_limit_timeout(
                    self.params.get("active_operations_limit_timeout"),
                    self.instance_service.Start,
                    StartInstanceRequest(instance_id=instance["id"]),
                )
                cloud_response = self.waiter(operation)

                response["response"] = MessageToDict(cloud_response)
                response = response_error_check(response)
            elif instance["status"] != "RUNNING":
                response["failed"] = True
                response["msg"] = (
                    "Current instance status(%s) doens`t allow start action"
                    % instance["status"]
                )
        else:
            response["failed"] = True
            response["msg"] = "Instance with such name(%s) doesn`t exist" % name

        return response

    def stop_vm(self):
        response = dict()
        response["changed"] = False
        folder_id = self.params.get("folder_id")
        name = self.params.get("name")
        instance = self._get_instance(name, folder_id)
        if instance:
            if instance["status"] == "RUNNING":
                operation = self.active_op_limit_timeout(
                    self.params.get("active_operations_limit_timeout"),
                    self.instance_service.Stop,
                    StopInstanceRequest(instance_id=instance["id"]),
                )
                cloud_response = self.waiter(operation)

                response["response"] = MessageToDict(cloud_response)
                response = response_error_check(response)
            elif instance["status"] != "STOPPED":
                response["failed"] = True
                response["msg"] = (
                    "Current instance status(%s) doens`t allow start action"
                    % instance["status"]
                )
        else:
            response["failed"] = True
            response["msg"] = "Instance with such name(%s) doesn`t exist" % name

        return response

    def get_info(self):
        response = dict()
        name = self.params.get("name")
        folder_id = self.params.get("folder_id")
        instance = self._get_instance(name, folder_id)
        if instance:
            response["instance"] = instance
        else:
            response["msg"] = "No instance found"
        return response


class PlatformId(Enum):
    IntelBroadwell = "standard-v1"
    IntelCascadeLake = "standard-v2"


class DiskType(Enum):
    HDD = "network-hdd"
    SSD = "network-ssd"


def _camel(snake_case):
    first, *others = snake_case.split("_")
    return "".join([first.lower(), *map(str.title, others)])


def _get_attached_disk_spec(disk_type, disk_size, image_id=None, snapshot_id=None):
    return (
        AttachedDiskSpec(
            auto_delete=True,
            disk_spec=AttachedDiskSpec.DiskSpec(
                type_id=disk_type, size=disk_size, image_id=image_id
            ),
        )
        if image_id
        else AttachedDiskSpec(
            auto_delete=True,
            disk_spec=AttachedDiskSpec.DiskSpec(
                type_id=disk_type, size=disk_size, snapshot_id=snapshot_id
            ),
        )
    )


def _get_secondary_disk_specs(secondary_disks):
    return list(
        map(
            lambda disk: AttachedDiskSpec(
                auto_delete=disk.get("autodelete", True),
                disk_spec=AttachedDiskSpec.DiskSpec(
                    description=disk.get("description"),
                    type_id=disk["type"],
                    size=disk["size"],
                ),
            ),
            secondary_disks,
        )
    )


def _get_resource_spec(memory, cores, core_fraction):
    return ResourcesSpec(memory=memory, cores=cores, core_fraction=core_fraction)


def _get_network_interface_spec(subnet_id, assign_public_ip):
    net_spec = [
        NetworkInterfaceSpec(
            subnet_id=subnet_id, primary_v4_address_spec=PrimaryAddressSpec()
        )
    ]
    if assign_public_ip:
        net_spec[0].primary_v4_address_spec.one_to_one_nat_spec.CopyFrom(
            OneToOneNatSpec(ip_version=IPV4)
        )
    return net_spec


def _get_scheduling_policy(preemptible):
    return SchedulingPolicy(preemptible=preemptible)


def main():
    argument_spec = vm_argument_spec()
    module = YccVM(
        argument_spec=argument_spec,
        mutually_exclusive=MUTUALLY_EXCLUSIVE,
        required_together=REQUIRED_TOGETHER,
        required_if=REQUIRED_IF,
    )
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    try:
        if module.params.get("state"):
            response = module.manage_states()
        elif module.params.get("operation"):
            response = module.manage_operations()
        else:
            raise Exception("One of the state/operation should be provided.")

    except Exception as error:  # pylint: disable=broad-except
        if hasattr(error, "details"):
            response["msg"] = getattr(error, "details")()
            response["exception"] = traceback.format_exc()
        else:
            response["msg"] = "Error during runtime occurred"
            response["exception"] = traceback.format_exc()
        module.fail_json(**response)

    module.exit_json(**response)


if __name__ == "__main__":
    main()
