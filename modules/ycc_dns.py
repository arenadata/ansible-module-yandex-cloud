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
module: ycc_dns
short_description: Ansible module to manage dns records in Yandex compute cloud
description:
    - "Ansible module to manage manage dns records in Yandex compute cloud"

options:
    token:
        description:
            - Oauth token to access cloud.
        type: str
        required: true
    dns_zone_id:
        description:
            - DNS zone ID - must be unique throw all DNS zones of cloud.
        type: str
        required: false
    folder_id:
        description:
            - DNS zone target folder id.
        type: str
        required: false
    service:
        description:
            - Service name for DNS record. Example: ranger.ru-central1.internal.
        type: str
        required: false
    ip:
        description:
            - IP for DNS record.
        type: str
        required: false
    dns_zone:
        description:
            - DNS zone, for DNS records. Default: internal.
        type: str
        required: false
    dns_prefix:
        description:
            - DNS zone prefix, for DNS records. Example: ru-central1 in ranger.ru-central1.internal.
        type: str
        required: false                                     
    operation:
        description:
            - get_zone_info_by_id
            - list_dns_zones_by_folder
            - list_dns_records_by_zone_id
            - add_dns_records_to_zone_id
            - get_dns_zone_id_by_name
        type: str
        required: true

"""

EXAMPLES = """
      ycc_dns:
        auth:
          token: some token
        folder_id: folder_id 
        dns_zone: "internal."
        operation: get_dns_zone_id_by_name
"""

RETURN = """
'dnsZones':
    createdAt: ''
    description: ''
    folderId: ''
    id: ''
    name: ''
    privateVisibility: {}
    zone: ''
"""

# pylint: disable=wrong-import-position
import traceback

from ansible.module_utils.yc import YC  # pylint: disable=E0611, E0401
from google.protobuf.json_format import MessageToDict
from grpc import StatusCode
from grpc._channel import _InactiveRpcError

from yandex.cloud.dns.v1.dns_zone_service_pb2 import (
    GetDnsZoneRequest,
    ListDnsZonesRequest,
    ListDnsZoneRecordSetsRequest,
    UpdateRecordSetsRequest
)
from yandex.cloud.dns.v1.dns_zone_service_pb2_grpc import DnsZoneServiceStub

DNS_OPERATIONS = [
    "get_zone_info_by_id",
    "list_dns_zones_by_folder",
    "list_dns_records_by_zone_id",
    "add_dns_records_to_zone_id",
    "get_dns_zone_id_by_name",
    "delete_dns_records_from_zone_id",
]


def dns_argument_spec():
    return dict(
        dns_zone_id=dict(type="str", required=False),
        folder_id=dict(type="str", required=False),
        service=dict(type="str", required=False),
        ip=dict(type="str", required=False),
        dns_zone=dict(type="str", required=False),
        dns_prefix=dict(type="str", required=False),
        operation=dict(choices=DNS_OPERATIONS, required=True),
    )


class YccDNS(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dns_service = self.sdk.client(DnsZoneServiceStub)

    def _get_zone_info_by_id(self, dns_zone_id):
        try:
            return MessageToDict(self.dns_service.Get(GetDnsZoneRequest(dns_zone_id=dns_zone_id)))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def _list_dns_zones_by_folder(self, folder_id, dns_zone=""):
        try:
            return MessageToDict(self.dns_service.List(ListDnsZonesRequest(
                folder_id=folder_id,
                filter=dns_zone
            )))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def _list_dns_records_by_zone_id(self, dns_zone_id):
        try:
            return MessageToDict(self.dns_service.ListRecordSets(ListDnsZoneRecordSetsRequest(
                dns_zone_id=dns_zone_id,
                page_size=200
            )))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def _add_dns_records_to_zone_id(self, dns_zone_id, record, dns_prefix, ip):
        try:
            return MessageToDict(self.dns_service.UpdateRecordSets(UpdateRecordSetsRequest(
                dns_zone_id=dns_zone_id,
                additions=[
                    {
                        "name": record + dns_prefix,
                        "type": "A",
                        "ttl": 600,
                        "data": [
                            ip
                        ]
                    }
                ]
            )))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def _delete_dns_records_from_zone_id(self, dns_zone_id, record, dns_prefix, ip):
        try:
            return MessageToDict(self.dns_service.UpdateRecordSets(UpdateRecordSetsRequest(
                dns_zone_id=dns_zone_id,
                deletions=[
                    {
                        "name": record + dns_prefix,
                        "type": "A",
                        "ttl": 600,
                        "data": [
                            ip
                        ]
                    }
                ]
            )))
        except _InactiveRpcError as err:
            if err._state.code is StatusCode.INVALID_ARGUMENT:  # pylint: disable=W0212
                return dict()
            else:
                raise err

    def manage_operations(self):  # pylint: disable=inconsistent-return-statements
        operation = self.params.get("operation")

        if operation == "get_zone_info_by_id":
            return self.get_zone_info_by_id()
        if operation == "list_dns_zones_by_folder":
            return self.list_dns_zones_by_folder()
        if operation == "list_dns_records_by_zone_id":
            return self.list_dns_records_by_zone_id()
        if operation == "add_dns_records_to_zone_id":
            return self.add_dns_records_to_zone_id()
        if operation == "delete_dns_records_from_zone_id":
            return self.delete_dns_records_from_zone_id()
        if operation == "get_dns_zone_id_by_name":
            return self.get_dns_zone_id_by_name()

    def get_zone_info_by_id(self):
        response = dict()
        dns_zone_id = self.params.get("dns_zone_id")
        dns = self._get_zone_info_by_id(dns_zone_id)
        if not dns_zone_id:
            response["msg"] = "No such dns_zone_id"
            return response
        response["dns_zone_info"] = dns
        return response

    def list_dns_zones_by_folder(self):
        response = dict()
        folder_id = self.params.get("folder_id")
        zones = self._list_dns_zones_by_folder(folder_id)
        if not folder_id:
            response["msg"] = "No such folder_id"
            return response
        response["dns_zones_list"] = zones
        return response

    def get_dns_zone_id_by_name(self):
        response = dict()
        folder_id = self.params.get("folder_id")
        dns_zone = self.params.get("dns_zone")
        zone = self._list_dns_zones_by_folder(folder_id, f"zone='{dns_zone}'")
        if not folder_id:
            response["msg"] = "No such folder_id"
            return response
        response["dns_zones_list"] = zone
        return response

    def list_dns_records_by_zone_id(self):
        response = dict()
        dns_zone_id = self.params.get("dns_zone_id")
        records = self._list_dns_records_by_zone_id(dns_zone_id)
        if not dns_zone_id:
            response["msg"] = "No such dns_zone_id"
            return response

        names = [record['name'] for record in records.get("recordSets")]

        response["dns_records_names"] = names

        return response

    def add_dns_records_to_zone_id(self):
        response = dict()
        dns_zone_id = self.params.get("dns_zone_id")
        record = self.params.get("service")
        ip = self.params.get("ip")
        dns_zone = self.params.get("dns_zone")
        dns_prefix = self.params.get("dns_prefix")
        existed_records = self.list_dns_records_by_zone_id()
        if f"{record}{dns_prefix}.{dns_zone}" not in existed_records["dns_records_names"]:
            record = self._add_dns_records_to_zone_id(dns_zone_id, record, dns_prefix, ip)
            if not dns_zone_id:
                response["msg"] = "No such dns_zone_id"
                return response
            response["record"] = record
            return response
        else:
            response["msg"] = "This dns record already exist"
            return response

    def delete_dns_records_from_zone_id(self):
        response = dict()
        dns_zone_id = self.params.get("dns_zone_id")
        record = self.params.get("service")
        ip = self.params.get("ip")
        dns_zone = self.params.get("dns_zone")
        dns_prefix = self.params.get("dns_prefix")
        existed_records = self.list_dns_records_by_zone_id()
        if f"{record}{dns_prefix}.{dns_zone}" in existed_records["dns_records_names"]:
            record = self._delete_dns_records_from_zone_id(dns_zone_id, record, dns_prefix, ip)
            if not dns_zone_id:
                response["msg"] = "No such dns_zone_id"
                return response
            response["record"] = record
            return response
        else:
            response["msg"] = "This dns record does not exist in DNS zone"
            return response


def main():
    argument_spec = dns_argument_spec()
    module = YccDNS(argument_spec=argument_spec)
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
