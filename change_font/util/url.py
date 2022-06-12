from urllib.parse import quote


def encode(val):
    val = quote(val, 'utf-8')
    return val


def url_format_list(parameters):
    param_list = []
    for (k, v) in parameters:
        param_str = '{}={}'.format(k, v)
        param_list.append(param_str)
    string_to_sign = '&'.join(param_list)
    return string_to_sign


def url_format(parameters):
    param_list = []
    for key, value in parameters.items():
        param_str = '{}={}'.format(key, value)
        param_list.append(param_str)
    string_to_sign = '&'.join(param_list)
    return string_to_sign
