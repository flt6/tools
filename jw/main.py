import hashlib
import requests
import re
import json
import base64
import tenacity as retry

def recapture(username, password, b64, ID):
    data = {"username": username, "password": password, "ID": ID, "b64": b64, "version": "3.1.1"}
    data_json = json.dumps(data)
    result = json.loads(requests.post("http://www.fdyscloud.com.cn/tuling/predict", data=data_json).text)
    return result


def pwd_md5(string: str) -> str:
    md5_part1 = hashlib.md5((string + "{Urp602019}").encode()).hexdigest().lower()
    md5_part2 = hashlib.md5(string.encode()).hexdigest().lower()
    final_result = md5_part1 + '*' + md5_part2
    return final_result

@retry.retry(stop=retry.stop_after_attempt(3), wait=retry.wait_random(3,5),reraise=True)
def login(username: str, password: str) -> requests.Session:
    print("正在登录...")
    session = requests.Session()

    req = session.get("http://jwstudent.lnu.edu.cn/login")
    req.raise_for_status()
    html = req.text
    match = re.search(r'name="tokenValue" value="(.+?)">', html)
    if match:
        token_value = match.group(1)
    else:
        raise ValueError("未找到 tokenValue")

    req = session.get("http://jwstudent.lnu.edu.cn/img/captcha.jpg")
    req.raise_for_status()
    im = req.content
    b64 = base64.b64encode(im).decode('utf-8')
    captcha_code = recapture(username="fbcfbc6", password="b0qDHNSSg5LxBRzO3hfpbTE5", b64=b64, ID="04897896")["data"]["result"]
    with open("captcha.jpg", "wb") as f:
        f.write(im)
    print(captcha_code)

    hashed_password = pwd_md5(password)

    # 模拟请求的 payload
    payload = {
        "j_username": username,
        "j_password": hashed_password,
        "j_captcha": captcha_code,
        "tokenValue": token_value
    }

    # 发送 POST 请求
    url = "http://jwstudent.lnu.edu.cn/j_spring_security_check"  # 替换为实际登录地址
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = session.post(url, data=payload, headers=headers)

    if "发生错误" in response.text:
        err = re.search(r'<strong>发生错误！</strong>(.+)', response.text)
        if err:
            error_message = err.group(1).strip()
            raise ValueError(f"登录失败: {error_message}")
        raise ValueError("登录失败")
    return session


print(login("20211299305", "123"))