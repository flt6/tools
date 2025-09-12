import time
import random
import hmac
import hashlib
import requests
from datetime import datetime
import json
from serverchan_sdk import sc_send; 


from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode

URL      = "http://[your libseat url]" 
# UID      = "[uid]"      # 图书馆账号
PWD      = "000000" # 图书馆密码
USERNAME = "[username]" # 验证码平台用户名
PASSWORD = "[password]" # 验证码平台密码
TOKEN    = "[token]"

def encrypt(t, s="server_date_time", e="client_date_time"):
    key = s.encode('utf-8')
    iv = e.encode('utf-8')
    data = t.encode('utf-8')
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(data, AES.block_size))  # Pkcs7 padding
    ct_base64 = b64encode(ct_bytes).decode('utf-8')
    return ct_base64+"_encrypt"

def b64_api(username, password, b64, ID):
    data = {"username": username, "password": password, "ID": ID, "b64": b64, "version": "3.1.1"}
    data_json = json.dumps(data)
    result = json.loads(requests.post("http://www.fdyscloud.com.cn/tuling/predict", data=data_json).text)
    return result

def recapture():
    res = requests.get(URL+"/auth/createCaptcha")
    ret = res.json()
    im =  ret["captchaImage"][21:]
    result = b64_api(username=USERNAME, password=PASSWORD, b64=im, ID="04897896")
    return ret["captchaId"],result["data"]["result"]

def login(username,password):
    captchaId, ans = recapture()
    url = URL+"/rest/auth"
    parm = {
        "answer": ans.lower(),
        "captchaId": captchaId,
    }
    headers = build_head("post", None)
    headers.update({
        "Username": encrypt(username),
        "Password": encrypt(password),
        "Logintype": "PC"
    })
    res = requests.post(url, headers=headers, params=parm)
    # print("Status:", res.status_code)
    ret = res.json()
    # print("Response:", ret)
    if ret["status"] == "fail":
        return None
    else:
        return ret["data"]["token"]

def generate_uuid():
    hex_digits = '0123456789abcdef'
    e = [random.choice(hex_digits) for _ in range(36)]
    e[14] = '4'
    e[19] = hex_digits[(int(e[19], 16) & 0x3) | 0x8]
    for i in [8, 13, 18, 23]:
        e[i] = '-'
    return ''.join(e)

def g(e: str):
    uuid = generate_uuid()
    timestamp = int(time.time() * 1000)
    r = f"seat::{uuid}::{timestamp}::{e.upper()}"
    secret_key = b"leos3cr3t"
    hmac_obj = hmac.new(secret_key, r.encode('utf-8'), hashlib.sha256)
    request_key = hmac_obj.hexdigest()
    return {
        "id": uuid,
        "date": timestamp,
        "requestKey": request_key
    }
    
def build_head(e: str,token:str):
    sig = g(e)
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-hmac-request-key": sig["requestKey"],
        "X-request-date": str(sig["date"]),
        "X-request-id": sig["id"]
    }
    if token is None:
        headers.pop("Authorization")
    return headers

def get_floor_data(token: str,buildingId= "1"):
    date = datetime.now().strftime("%Y-%m-%d")  # 获取当前日期
    url = f"{URL}/rest/v2/room/stats2/{buildingId}/{date}"
    params = {
        "buildingId": buildingId,
        "date": date,
        "token": token
    }
    headers = build_head("get",token)

    response = requests.get(url, headers=headers, params=params)

    print("Status:", response.status_code)
    res = response.json()
    if res["status"] != "success":
        print("Error:", res)
        return -1
    else:
        ret = []
        for room in res["data"]:
            ret.append({"roomId": room["roomId"], "room": room["room"], "free": room["free"], "inUse": room["inUse"], "totalSeats": room["totalSeats"]})
            # print(f"Room ID: {room['roomId']}, Name: {room['room']}, free: {room['free']}, inUse: {room['inUse']}, total: {room['totalSeats']}")
        return ret

def get_room_data(token: str,id:str = "10"):
    date = datetime.now().strftime("%Y-%m-%d")  # 获取当前日期
    # 替换为目标接口地址
    print(date)
    url = f"{URL}/rest/v2/room/layoutByDate/{id}/{date}"
    params = {
        "id": id,
        "date": date,
        "token": token
    }

    sig = g("get")
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-hmac-request-key": sig["requestKey"],
        "X-request-date": str(sig["date"]),
        "X-request-id": sig["id"]
    }

    response = requests.get(url, headers=headers, params=params)

    print("Status:", response.status_code)
    ret = response.json()
    if ret["status"] != "success":
        print("Error:", ret)
        return -1
    else:
        print("Data:", ret["data"]["name"])
    print("Response:", )

def send_message(msg):
    print(sc_send(TOKEN, "图书馆座位", msg))

def main(dep=0):
    if dep>3:
        print("无法获取数据！")
        send_message("无法获取数据！")
        return
    years = [2021, 2022, 2023, 2024]
    house = []
    classes = [1,2,3]
    num = range(1,21)
    token = None
    try:
        print("正在尝试登录...")
        tried =0
        while token is None and tried <= 5:
            # id = UID
            id = str(random.choice(years)) + random.choice(house) + str(random.choice(classes)) + str(random.choice(num)).zfill(2)
            token = login(id,PWD)
            if token is None:
                print("登陆失败：",token)
                time.sleep(random.randint(10, 30))
            tried += 1
        if token is None:
            print("登录失败，请检查账号密码或网络连接。")
            main(dep+1)
            return
        print("登录成功，Token:", token)
        data = get_floor_data(token, "1")  # 获取一楼数据
        if data == -1:
            print("获取数据失败，请检查网络连接或Token是否有效。")
            main(dep+1)
        else:
            ret = []
            for room in data:
                if room["free"] > 0:
                    ret.append(room)
            if ret:
                msg = "|区域|空座|占用率|\n|-|-|-|\n"
                for room in ret:
                    msg += f"|{room['room']}|{room['free']}|{1-room['free']/room['totalSeats']:0.2f}|\n"
                send_message(msg)
    except Exception as e:
        print("发生错误:", e)
        main(dep+1)

if __name__ == "__main__":
    main()
