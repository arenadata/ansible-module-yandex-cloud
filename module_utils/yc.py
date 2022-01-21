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

import re
from time import sleep

from ansible.module_utils.basic import AnsibleModule
from yandexcloud import SDK, RetryInterceptor


def yc_argument_spec():
    return dict(
        auth=dict(type='dict', options=dict(
            token=dict(type="str", required=False, default=None),
            service_account_key=dict(type="dict", required=False, default=None),
            endpoint=dict(type="str", required=False, default='api.cloud.yandex.net'),
            root_certificates=dict(type="str", required=False, default=None))))


class YC(AnsibleModule):
    def __init__(self, *args, **kwargs):
        argument_spec = yc_argument_spec()
        argument_spec.update(kwargs.get("argument_spec", dict()))
        kwargs["argument_spec"] = argument_spec
        super().__init__(*args, **kwargs)

        if not (self.params["auth"]["token"] or self.params["auth"]["service_account_key"]):
            self.fail_json(msg="authorization token or service account key should be provided.")

        interceptor = RetryInterceptor(max_retry_count=10)
        if self.params["auth"]["root_certificates"]:
            self.params["auth"]["root_certificates"] = self.params["auth"]["root_certificates"].encode("utf-8")
        self.sdk = SDK(interceptor=interceptor, **self.params["auth"])
        if self.params.get("fqdn") and not self.params.get("name"):
            self.params["name"] = self.params["fqdn"].split('.')[0]
        if self.params.get("name"):
            if not re.match('^[a-z][a-z0-9-]{1,61}[a-z0-9]$', self.params["name"]):
                self.fail_json(msg=f'bad name {self.params["name"]}, see Yandex Cloud requirements for name')
        if self.params.get("hostname"):
            if not re.match('^[a-z][a-z0-9-]{1,61}[a-z0-9]$', self.params["hostname"]):
                self.fail_json(msg=f'bad hostname {self.params["hostname"]}, see Yandex Cloud requirements for hostname')

    def waiter(self, operation):
        waiter = self.sdk.waiter(operation.id)
        for _ in waiter:
            sleep(1)
        return waiter.operation


def response_error_check(response):
    if "response" not in response or response["response"].get("error"):
        response["failed"] = True
        response["changed"] = False
    else:
        response["changed"] = True
    return response
