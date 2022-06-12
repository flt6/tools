import requests

application_json = 'application/json'
application_x_www_form_urlencoded = 'application/x-www-form-urlencoded'
multipart_formdata = 'multipart/form-data'
multipart_encoder = 'multipart_encoder'
binary = 'binary'


def send_delete(url, headers):
    response = requests.delete(url, headers=headers)
    return response.content.decode("utf-8")


def send_get(url, params, headers):
    response = requests.get(url=url, params=params, headers=headers)
    return response.content.decode("utf-8")


def send_post(url, request_body, headers):
    content_type = headers['content-type']
    if application_json == content_type:
        response = requests.post(url, json=request_body, headers=headers)
    elif multipart_formdata == content_type:
        data = get_multipart_data(request_body,headers)
        response = requests.post(url, data=data, headers=headers)
    else:
        response = requests.post(url, data=request_body, headers=headers)

    return response.content.decode("utf-8")


def send_put(url, request_body, headers):
    content_type = headers['content-type']
    if application_json == content_type:
        response = requests.put(url, json=request_body, headers=headers)
    elif multipart_formdata == content_type:
        data = get_multipart_data(request_body,headers)
        response = requests.put(url, data=data, headers=headers)
    else:
        response = requests.put(url, data=request_body, headers=headers)

    return response.content.decode("utf-8")


def send_patch(url, request_body, headers):
    content_type = headers['content-type']
    if application_json == content_type:
        response = requests.patch(url, json=request_body, headers=headers)
    elif multipart_formdata == content_type:
        data = get_multipart_data(request_body,headers)
        response = requests.patch(url, data=data, headers=headers)
    else:
        response = requests.patch(url, data=request_body, headers=headers)

    return response.content.decode("utf-8")


def get_multipart_data(request_body,headers):
    data = request_body['multipart_encoder']
    headers['content-type'] = data.content_type

    return data