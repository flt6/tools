from requests import Response,Session
from re import search
from json import dumps

headers = {
   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42'
}
s=Session()

def chk(resp:Response):
    if resp.status_code != 200:
        print("Error: %d" % resp.status_code)
        exit(1)
    return resp.text

def get(url,**kwargs):
    ret = s.get(url,allow_redirects=False,headers=headers,**kwargs)
    jar = ret.cookies
    if ret.status_code == 302:
        url2 = ret.headers['Location']
        return get(url2, cookies=jar)
    elif ret.status_code != 200:
        print("Error: %d" % ret.status_code)
        exit(1)
    return ret

def login(username, password):
    # 问卷星竟然明文发送密码
    ret = chk(s.get("https://www.wjx.cn/login.aspx"))
    v1 = search('(?<=(<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value=")).+(?=(" />))',ret)
    if v1 is not None:
        v1 = v1.group()
    v2 = search('(?<=(<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value=")).+(?=(" />))',ret)
    if v2 is not None:
        v2 = v2.group()
    v3 = search('(?<=(<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value=")).+(?=(" />))',ret)
    if v3 is not None:
        v3 = v3.group()
    print(v1,v2,v3)
    with open("tmp.html", "w",encoding="utf-8") as f:
        print(ret,file=f)
    d={
        "__VIEWSTATE":          v1,
        "__VIEWSTATEGENERATOR": v2,
        "__EVENTVALIDATION":    v3,
        "UserName":             username,
        "Password":             password,
        "LoginButton":          "登录"
    }
    # d={
    #     "__VIEWSTATE":         "/wEPDwULLTIxMTQ1NzY4NzFkGAEFHl9fQ29udHJvbHNSZXF1aXJlUG9zdEJhY2tLZXlfXxYBBQpSZW1lbWJlck1ldLwU4qgz33Rji8zou8eAENNib4k=",
    #     "__VIEWSTATEGENERATOR":"C2EE9ABB",
    #     "__EVENTVALIDATION":   "/wEdAAfxrqR6nVOy3mBYlwdwNQ3ZR1LBKX1P1xh290RQyTesRRHS0B3lkDg8wcTlzQR027xRgZ0GCHKgt6QG86UlMSuIXArz/WCefbk6V2VE3Ih52ScdcjStD50aK/ZrfWs/uQXcqaj6i4HaaYTcyD0yJuxuNMxKZaXzJnI0VXVv9OL2HZrk5tk=",
    #     "UserName":            username,
    #     "Password":            password,
    #     "LoginButton":         "登录"
    # }
    ret = s.post("https://www.wjx.cn/Login.aspx",json=dumps(d))
    ret.raise_for_status()

def getlist(id):
    ret = s.get(
        "https://www.wjx.cn/wjx/activitystat/viewstatsummary.aspx",
        params={"activity":id},
        headers=headers        
    )
    ret = chk(ret)
    find = search(r'(?<=(var ids = "))[\d,]+(?=(";))',ret)
    assert find is not None,ret
    return find.group().split(",")

if __name__ == "__main__":
    login("flt","**************")
    print(s.cookies)
    print(getlist("184412487"))