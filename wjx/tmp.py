import requests

url = "https://www.wjx.cn/login.aspx"

payload={}
headers = {
   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)