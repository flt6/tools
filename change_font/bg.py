from req import Req
from json import dump
from time import  sleep
from base64 import b64decode
import pickle

# cnter='7'
url="https://openai.100tal.com/aiimage/comeducation"
# file=f"opt/{str(cnter)}new.jpg"
file="opt/DINGTALK_IM_1659828452.JPGnew.JPG"
req=Req(warn=False)
if not req.ready:
    id=input("ID: ")
    sec=input("Secret: ")
    req.set(id,sec)
bgpic=req("http://openai.100tal.com/aiimage/handwriting-erase",file)

if bgpic["code"]!=20000:
    print(bgpic)
    with open("bg.json","w",encoding="utf-8") as f:
        dump(bgpic,f)
    exit(-1)
with open("bg.png","wb") as f:
    f.write(b64decode(bgpic["image_base64"]))