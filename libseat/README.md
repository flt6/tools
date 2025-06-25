# 某校图书馆预约系统分析

登录界面如图
![登录](https://oss.flt6.top/imgs/202506081117287.png?x-oss-process=style/init)

输入任意账号、密码，正确填验证码，F12抓包。注意到访问`http://[URL]/rest/auth?answer=bmx8&captchaId=qxtd5hl5h8wz`，返回`{"status":"fail","code":"13","message":"登录失败: 用户名或密码不正确","data":null}`且无其他访问，确定为登录API。
观察url参数，未发现账号密码；请求为GET不存在data。仔细观察请求体，注意到headers中有username和password，测试证明为账号密码。
![登录API](https://oss.flt6.top/imgs/202506081117743.png?x-oss-process=style/init)
显然账号密码加密，尝试直接重放请求失败，注意到headers中的`x-hmac-request-key`等，推测存在加密。

## headers中的`X-hmac-request-key`等参数

全局搜索关键字`x-hmac-request-key`，找到唯一代码
```javascript
{
    var t = "";
    t = "post" === e.method ? g("post") : g("get"),
    e.headers = c()({}, e.headers, {
        Authorization: sessionStorageProxy.getItem("token"),
        "X-request-id": t.id,
        "X-request-date": t.date,
        "X-hmac-request-key": t.requestKey
    })
}
```
动态调试找到`g`的实现
```
function g(e) {
    var t = function() {
        for (var e = [], t = 0; t < 36; t++)
            e[t] = "0123456789abcdef".substr(Math.floor(16 * Math.random()), 1);
        return e[14] = "4",
        e[19] = "0123456789abcdef".substr(3 & e[19] | 8, 1),
        e[8] = e[13] = e[18] = e[23] = "-",
        e.join("")
    }()
        , n = (new Date).getTime()
        , r = "seat::" + t + "::" + n + "::" + e.toUpperCase()
        , o = p.a.decrypt(h.default.prototype.$NUMCODE);
    return {
        id: t,
        date: n,
        requestKey: m.HmacSHA256(r, o).toString()
    }
}
```

注意到`o = p.a.decrypt(h.default.prototype.$NUMCODE);`未知，确定`h.default.prototype.$NUMCODE`是常量，且`p.a.decrypt`与时间无关，直接动态调试拿到解密结果`o=leos3cr3t`.

其他算法实现均未引用其他代码，转写为python
```python
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
```

至此，使用上述`g`动态生成hmac后，其他内容不变条件下成功重放请求，可以拿到登录token。

注意到账号密码均加密，尝试逆向。

## 账号密码加密

从`http://[URL]/rest/auth?answer=bmx8&captchaId=qxtd5hl5h8wz`请求的启动器中找到关键函数`handleLogin`
![启动器](https://oss.flt6.top/imgs/202506081117170.png?x-oss-process=style/init)
```javascript
handleLogin: function() {
    var t = this;
    if ("" == this.form.username || "" == this.form.password)
        return this.$alert(this.$t("placeholder.accountInfo"), this.$t("common.tips"), {
            confirmButtonText: this.$t("common.confirm"),
            type: "warning",
            callback: function(t) {}
        });
    this.loginLoading = !0,
    Object(m.y)({
        username: d(this.form.username) + "_encrypt",
        password: d(this.form.password) + "_encrypt",
        answer: this.form.answer,
        captchaId: this.captchaId
    }).then(function(s) {
        "success" == s.data.status ? (sessionStorageProxy.setItem("loginType", "login"),
        sessionStorageProxy.setItem("token", s.data.data.token),
        t.loginLoading = !1,
        t.getUserInfoFunc()) : (t.$warning(s.data.message),
        t.refreshCode(),
        t.clearLoginForm(),
        t.loginLoading = !1)
    }).catch(function(s) {
        console.log("出错了:", s),
        t.$error(t.$t("common.networkError")),
        t.loginLoading = !1
    })
},
```
注意到
```javascript
username: d(this.form.username) + "_encrypt",
password: d(this.form.password) + "_encrypt",
```
动态调试找到`d`的实现
```
var ....
    , l = "server_date_time"
    , u = "client_date_time"
    , d = function(t) {
    var s = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : l
        , e = arguments.length > 2 && void 0 !== arguments[2] ? arguments[2] : u
        , a = r.a.enc.Utf8.parse(e)
        , i = r.a.enc.Utf8.parse(s)
        , n = r.a.enc.Utf8.parse(t);
    return r.a.AES.encrypt(n, i, {
        iv: a,
        mode: r.a.mode.CBC,
        padding: r.a.pad.Pkcs7
    }).toString()
}
```
显然`arguments.length`恒为1，故`s=l="server_date_time"`，`e=u="client_date_time"`，至此AES加密的参数均已知，python实现该AES加密后验证使用的AES为标准AES加密。
故python实现账号密码的加密：
```python
def encrypt(t, s="server_date_time", e="client_date_time"):
    key = s.encode('utf-8')
    iv = e.encode('utf-8')
    data = t.encode('utf-8')
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(data, AES.block_size))  # Pkcs7 padding
    ct_base64 = b64encode(ct_bytes).decode('utf-8')
    return ct_base64+"_encrypt"
```

关于验证码，`http://[URL]/auth/createCaptcha`返回验证码base64，提交时为URL参数，均未加密。
至此，完成整个登录过程的逆向。

## 其他API

所有其他API请求headers均带有`X-hmac-request-key`，逻辑同上。URL参数中的token为登录API返回值。

## 完整demo

这是一个座位检查demo，查询某个区域是否有余座，如有则通过`serverchan_sdk`发生通知。
需按照实际情况修改常量。
为了识别验证码，调用了某验证码识别API，该平台为收费API，与本人无关，不对此负责，如有违规烦请告知。

Github账号出问题了只能直接贴代码了

```python
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
UID      = "[uid]"      # 图书馆账号
PWD      = "[password]" # 图书馆密码
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
            id = UID
            # id = str(random.choice(years)) + random.choice(house) + str(random.choice(classes)) + str(random.choice(num)).zfill(2)
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

```

