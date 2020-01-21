import os
from time import sleep

import grpc
from ansible.module_utils.basic import AnsibleModule
from yandexcloud import SDK, RetryInterceptor


def yc_argument_spec():
    return dict(
        token=dict(type='str', required=False, default=os.environ.get('yc_token'))
    )


class YC(AnsibleModule):
    def __init__(self, *args, **kwargs):
        argument_spec = yc_argument_spec()
        argument_spec.update(kwargs.get('argument_spec', dict()))
        kwargs['argument_spec'] = argument_spec

        super().__init__(*args, **kwargs)
        interceptor = RetryInterceptor(max_retry_count=5, retriable_codes=[grpc.StatusCode.UNAVAILABLE])
        self.sdk = SDK(interceptor=interceptor, token=self.params.get('token'))

    def waiter(self, operation):
        waiter = self.sdk.waiter(operation.id)
        for _ in waiter:
            sleep(1)
        return waiter.operation
