# -*- coding: utf-8 -*-
"""
author: yu.hailong
email: yuhailong@100tal.com
datetime: 2020/4/23 2:34 下午
description：
urlencoded methods
"""

import time
from util.send_sign_http import send_request
from util.http import application_json


class ApplicationJsonMethods:
    def __init__(self, ACCESS_KEY_ID:str, ACCESS_KEY_SECRET:str) -> None:
        '''
            @brief 以json形式发送数据
            @param ACCESS_KEY_ID:     注册应用时的ACCESS_KEY_ID
            @param ACCESS_KEY_SECRET：注册应用时的ACCESS_KEY_SECRET
        '''
        self.header = application_json
        self.ACCESS_KEY_ID = ACCESS_KEY_ID
        self.ACCESS_KEY_SECRET = ACCESS_KEY_SECRET

    def response(self, method:str, HTTP_URL:str, body_params=None,payload={}):
        '''
        @parms: 
            method: GET、POST、PUT、PATCH、DELETE
        '''
        assert body_params is not None

        # 获取当前时间（东8区）
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

        result = send_request(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET, timestamp, HTTP_URL, payload, body_params, method,
                              self.header)
        return result

    def get(self, *args, **kwargs):
        method="GET"
        return self.response(method,*args,**kwargs)

    def post(self, *args, **kwargs):
        method="POST"
        return self.response(method,*args,**kwargs) 
    
    def delete(self, *args, **kwargs):
        method = "DELETE"
        return self.response(method,*args,**kwargs) 

    