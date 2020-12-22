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
module: cloud_init
short_description: Ansible module to manage cloud-init timeout 
version_added: "2.4"
description:
    - "Ansible module to manage cloud-init timeout"

options:
    cloud_init_timeout:
      type: integer
      display_name: "Cloud-init timeout"
      ui_options:
        advanced: true
      required: false
      description: "Timeout for cloud-init to finish running tasks, in seconds"
"""


EXAMPLES = """
- name: "Wait for cloud-init to finish"
  cloud_init:
    cloud_init_timeout: 60

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
import traceback
from ansible.module_utils.yc import YC


def cloud_init_spec():
    return dict(
        cloud_init_timeout=dict(type="int", required=False, default=600)
    )


class CloudInit(YC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def cloud_init_wait(self):
        timeout = self.params.get("cloud_init_timeout")
        while timeout > 0:
            self.run_command('cloud-init status')


def main():
    argument_spec = cloud_init_spec()
    module = CloudInit(argument_spec=argument_spec)
    response = dict()
    try:
        if module.params.get("cloud_init_timeout"):
            response = module.manage_operations()

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