import os

import grpc
from ansible.module_utils.basic import AnsibleModule
from yandexcloud import SDK, RetryInterceptor


def yc_argument_spec():
    return dict(
        token=dict(type='str', required=True, default=os.environ.get('yc_token'))
    )


class YC(AnsibleModule):
    def __init__(self, *args, **kwargs):
        argument_spec=yc_argument_spec()
        argument_spec.update(kwargs.get('argument_spec', dict()))
        kwargs['argument_spec'] = argument_spec

        super().__init__(*args, **kwargs)
        interceptor = RetryInterceptor(max_retry_count=5, retriable_codes=[grpc.StatusCode.UNAVAILABLE])
        self.sdk = SDK(interceptor=interceptor, token=argument_spec['token'])
