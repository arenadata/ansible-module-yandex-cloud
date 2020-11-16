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

import os
from time import sleep

from ansible.module_utils.basic import AnsibleModule
from yandexcloud import SDK, RetryInterceptor

ZONE_IDS = ["ru-central1-a", "ru-central1-b", "ru-central1-c"]


def yc_argument_spec():
    return dict(
        token=dict(type="str", required=False, default=os.environ.get("yc_token"))
    )


class YC(AnsibleModule):
    def __init__(self, *args, **kwargs):
        argument_spec = yc_argument_spec()
        argument_spec.update(kwargs.get("argument_spec", dict()))
        kwargs["argument_spec"] = argument_spec

        super().__init__(*args, **kwargs)
        interceptor = RetryInterceptor(max_retry_count=10)
        self.sdk = SDK(interceptor=interceptor, token=self.params.get("token"))

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
