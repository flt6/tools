from util.http import send_patch,send_post,send_delete,send_get,send_put
from util.sign_client import get_signature
from util.url import encode,url_format


def send_request(
        access_key_id,
        access_key_secret,
        timestamp,
        url,
        url_params,
        body_params,
        request_method,
        content_type
        ) -> str:
    if access_key_id is None or len(access_key_id) == 0:
        raise RuntimeError('参数access_key_id不能为空')
    if access_key_secret is None or len(access_key_secret) == 0:
        raise RuntimeError('参数access_key_secret不能为空')
    if timestamp is None or len(timestamp) == 0:
        raise RuntimeError('参数timestamp不能为空')
    if url is None or len(url) == 0:
        raise RuntimeError('参数url不能为空')
    if url_params is None:
        raise RuntimeError('参数url_params不能为空')
    if body_params is None:
        raise RuntimeError('参数body_params不能为空')
    if request_method is None or len(request_method) == 0:
        raise RuntimeError('参数request_method不能为空')
    if content_type is None or len(content_type) == 0:
        raise RuntimeError('参数content_type不能为空')

    url_params['access_key_id'] = access_key_id
    url_params['timestamp'] = timestamp

    signature, signature_nonce = get_signature(
        url_params,
        body_params,
        request_method,
        content_type,
        access_key_secret)

    url_params['signature'] = encode(signature)
    url_params['signature_nonce'] = signature_nonce
    url_params['timestamp'] = timestamp

    url = url + '?' + url_format(url_params)

    headers = {
        'content-type': content_type
    }

    result = None
    if request_method == 'POST':
        result = send_post(url, request_body=body_params, headers=headers)
    elif request_method == 'PATCH':
        result = send_patch(url, request_body=body_params, headers=headers)
    elif request_method == 'PUT':
        result = send_put(url, request_body=body_params, headers=headers)
    elif request_method == 'GET':
        result = send_get(url, params=None, headers=headers)
    elif request_method == 'DELETE':
        result = send_delete(url, headers=headers)
    else:
        raise RuntimeError('支持[GET、POST、PUT、PATCH、DELETE]请求方式')
    return result
