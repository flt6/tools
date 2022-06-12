#!/usr/bin/python
# -*- coding:utf-8 -*-

import base64
import hmac
from hashlib import sha1
import uuid
from urllib import parse
import json
from util.url import url_format_list
from util.http import application_x_www_form_urlencoded,application_json

__request_body = "request_body"


def __generate_signature(parameters, access_key_secret):
    sorted_parameters = sorted(parameters.items(), key=lambda parameters : parameters[0])
    string_to_sign = url_format_list(sorted_parameters)
    secret = access_key_secret + "&"

    # print(secret)
    h = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), sha1)
    signature = base64.b64encode(h.digest()).strip()
    signature = str(signature, encoding="utf8")
    # signature = bytes(signature, encoding="utf8")
    return signature


def get_signature(url_params, body_params, request_method, content_type, access_key_secret):
    signature_nonce = str(uuid.uuid1())

    sign_param = {
        'signature_nonce': signature_nonce
    }

    if (content_type == application_x_www_form_urlencoded or content_type == application_json) \
            and (request_method == 'POST' or request_method == 'PATCH' or request_method == 'PUT')\
            and body_params is not None and len(body_params) != 0:
        if content_type == application_x_www_form_urlencoded:
            sign_param[__request_body] = parse.urlencode(body_params)
        else:
            sign_param[__request_body] = json.dumps(body_params)
            # 生成签名使用Python，发送签名使用其他语言时使用separators
            # sign_param[__request_body] = json.dumps(body_params,separators=(',',':'))

    for key in url_params.keys():
        sign_param[key] = url_params[key]

    signature = __generate_signature(sign_param, access_key_secret)
    return signature, signature_nonce



