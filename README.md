# ansible-module-yandex-cloud

## Overview

ansible-module-yandex-cloud is a set of ansible modules that manage a yandex cloud

## Try it out

### Prerequisites

* The <https://github.com/yandex-cloud/python-sdk> module is required.

### Build & Run

1. pip install --user `git+https://github.com/yandex-cloud/python-sdk`
2. git clone `https://github.com/arenadata/ansible-module-yandex-cloud`
3. cd ansible-module-yandex-cloud

#### If run playbook.yml in this directory, then create ansible.cfg

```
[defaults]
library = ./modules
module_utils = ./module_utils
```

## Documentation

### VM managment

```raw
ycc_vm:
        Ansible module to manage (create/update/delete) virtial machines in Yandex compute cloud

  * This module is maintained by The Ansible Community
OPTIONS (= is mandatory):

- assign_public_ip
        Assign public address.
        [Default: False]
        type: bool

- core_fraction
        Guaranteed vCPU share
        [Default: 100]
        choises:
        - 5
        - 20
        - 50
        - 100

        type: int

- cores
        vCPU number.
        [Default: 2]
        type: int

- disk_size
        Primary disk size in GB.
        [Default: 10]
        type: int

- disk_type
        Primary disk type.
        [Default: hdd]
        choises: hdd, ssd
        type: str

= folder_id
        Virtual machine target folder id.

        type: str

- hostname
        Virtual machine hostname, default same as name.
        [Default: (null)]
        type: str

- image_id
        Boot image id.
        Required with `state=present'.
        [Default: (null)]
        type: str

- login
        User to create on virtual machine, required for linux instances.
        Required together with `public_ssh_key'.
        Required with `state=present', mutually exclusive with `metadata'.
        [Default: (null)]
        type: str

- max_retries
        Max retries to proceed operation/state.
        [Default: 5]
        type: int

- memory
        RAM size, GB.
        [Default: 2]
        type: int

- metadata
        Metadata to be translate to vm.
        [Default: (null)]
        type: dict

= name
        Virtual machine name - must be unique throw all folders of cloud.

        type: str

- operation
        stop, start, get_info or get_subnet_info.
        Mutually exclusive with `state'.
        [Default: (null)]
        choises: start, stop, get_info, get_subnet_info, update

- platform_id
        Platform id.
        [Default: Intel Broadwell.]
        choises: Intel Cascade Lake, Intel Broadwell
        type: str

- preemptible
        Create preemtible(may be stopped after working 24h a row) vm.
        [Default: False]
        type: bool

- public_ssh_key
        Created user`s openssh public key.
        Required together with `public_ssh_key'.
        Required with `state=present', mutually exclusive with `metadata'.
        [Default: (null)]
        type: str

- retry_multiplayer
        Retry multiplayer between retries to proceed operation/state
        (wait retry_multiplayer*curent_retry seconds)
        [Default: 2]
        type: int

- secondary_disks_spec
        Additional disk configuration spec.
        [Default: (null)]
        type: list

- state
        VM state.
        Mutually exclusive with `operation'.
        (Choices: present, absent)[Default: (null)]
        type: str

- subnet_id
        Network id.
        Required with `state=present'
        [Default: (null)]

- secondary_subnet_id
        Network id for creation secondary NIC.
        Please note that such options as assign_public_ip, assign_internal_ip, fqdn does not affect to secondary NIC.
        The security_groups option will apply to both interfaces.
        [Default: (null)]

= token
        Oauth token to access cloud.

        type: str

- zone_id
        Availability zone id.
        [Default: ru-central1-a]
        choises: ru-central1-a, ru-central1-b, ru-central1-c
        type: str


AUTHOR: Rotaru Sergey (rsv@arenadata.io)
        METADATA:
          status:
          - preview
          supported_by: community


EXAMPLES:

- name: Create vm
  ycc_vm:
    auth:
      token: {{ my_token }}
    name: myvm
    login: john_doe
    public_ssh_key: john_doe_public_key
    hostname: myvm
    zone_id: ru-central1-c
    folder_id: b1gotqhf076hh183dn
    platform_id: "Intel Cascade Lake"
    core_fraction: 100
    cores: 2
    memory: 2
    image_id: fd84uob96bu79jk8fqht
    disk_type: ssd
    disk_size: 50
    secondary_disks_spec:
      - autodelete: true
        description: disk1
        type: ssd
        size: 10
      - autodelete: false
        description: disk2
        type: hdd
        size: 100
    subnet_id: b0cccg656k0nixi92a
    secondary_subnet_id: e2l3dk5nid5fdegfthu4
    assign_public_ip: false
    preemptible: true
    metadata:
        user-data: "cloud init format in str"
    state: present

- name: Stop vm
  ycc_vm:
    token: {{ my_token }}
    name: myvm
    operation: stop

- name: Start vm
  ycc_vm:
    token: {{ my_token }}
    name: myvm
    operation: start


RETURN VALUES:

original_message:
    description: The original name param that was passed in
    type: str
    returned: always
message:
    description: The output message that the test module generates
    type: str
    returned: always
```
