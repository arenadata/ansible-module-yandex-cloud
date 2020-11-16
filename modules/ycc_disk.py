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
module: ycc_disk
short_description: Ansible module to manage virtial machines disks in Yandex compute cloud
version_added: "2.4"
description:
    - "Ansible module to manage virtial machines disks in Yandex compute cloud"

options:
    token:
        description:
            - Oauth token to access cloud.
        type: str
        required: true
    id:
        description:
            - Virtual disk id - must be unique throw all folders of cloud.
        type: str
        required: true
    operation:
        description:
            - get_info
        type: str
        required: true

"""


EXAMPLES = """
ycc_disk:
    token: some_token
    operation: get_info
    id: ef3rsa853oiu9tjhguqt
"""

RETURN = """
'disk':
    createdAt: ''
    folderId: ''
    id: ''
    instanceIds: []
    productIds: []
    size: ''
    sourceImageId: ''
    status: ''
    typeId: 'network-hdd'
    zoneId: 'ru-central1-c'
"""

# pylint: disable=wrong-import-position
import traceback

from ansible.module_utils.yc import YC  # pylint: disable=E0611, E0401
from google.protobuf.json_format import MessageToDict
from grpc import StatusCode
from grpc._channel import _InactiveRpcError
from yandex.cloud.compute.v1.disk_service_pb2 import GetDiskRequest
from yandex.cloud.compute.v1.disk_service_pb2_grpc import DiskServiceStub

DISK_OPERATIONS = ["get_info"]


def disk_argument_spec():
    return dict(
        id=dict(type="str", required=True),
        operation=dict(choices=DISK_OPERATIONS, required=True),
    )


class YccDisk(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.disk_service = self.sdk.client(DiskServiceStub)

    def _get_disk(self, disk_id):
        try:
            return MessageToDict(self.disk_service.Get(GetDiskRequest(disk_id=disk_id)))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def manage_operations(self):  # pylint: disable=inconsistent-return-statements
        operation = self.params.get("operation")

        if operation == "get_info":
            return self.get_info()

    def get_info(self):
        response = dict()
        id = self.params.get("id")
        disk = self._get_disk(id)
        if not disk:
            response["msg"] = "No such disk"
            return response
        response["disk"] = disk
        return response


def main():
    argument_spec = disk_argument_spec()
    module = YccDisk(argument_spec=argument_spec)
    response = dict()
    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    try:
        if module.params.get("operation"):
            response = module.manage_operations()
        else:
            raise Exception("One of the operation should be provided.")

    except Exception as error:  # pylint: disable=broad-except
        if hasattr(error, "details"):
            response["msg"] = getattr(error, "details")()
            response["exception"] = traceback.format_exc()
        else:
            response["msg"] = "Error during runtime ocurred"
            response["exception"] = traceback.format_exc()
        module.fail_json(**response)

    module.exit_json(**response)


if __name__ == "__main__":
    main()
