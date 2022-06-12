from util.sign_client import get_signature
from util.url import url_format,encode


def get_sign(
        access_key_id,
        access_key_secret,
        timestamp,
        url,
        url_params):
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

    url_params['access_key_id'] = access_key_id
    url_params['timestamp'] = timestamp

    signature, signature_nonce = get_signature(
        url_params,
        None,
        'GET',
        'application/application_json',
        access_key_secret)

    url_params["signature_nonce"] = signature_nonce
    url_params["signature"] = encode(signature)

    url = url + '?' + url_format(url_params)
    return url
