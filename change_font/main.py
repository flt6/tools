from req import Req
import cv2
import numpy as np
# from matplotlib import pyplot as plt
from json import dump
from PIL import ImageFont,Image,ImageDraw
from random import randint
from time import  sleep
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
data:dict=req(url,file,function=2,subject="liberat")
if "data" not in data.keys():
    print(data)
    exit(-1)
with open("data.conf","wb") as f:
    pickle.dump(data,f)



# with open("data.conf","rb") as f:
#     data=pickle.load(f)

data=data["data"]

img=cv2.imread("bg.png")
rows,cols,_=img.shape
fontbase=ImageFont.truetype("font.ttf",100)
arr=[]
cnt=-1

for string in data["result"]:
    length=len(string["texts"])
    size=0
    temp=cnt+1
    for char in string["char_info"]:
        x0,y0=char["pos"][0].values()
        x1,y1=char["pos"][2].values()
        size+=(max(x1-x0,y1-y0)+min(x1-x0,y1-y0))/2
        arr.append([x0,x1,y0,y1,char["char"],None])
        # img[(y0-2):(y1+2),(x0-2):(x1+2)]=(255,255,255)
        cnt+=1
    arr[temp][5]=int(size//(length-4))

# cv2.imwrite("background.png",img)
img_pil=Image.fromarray(img)
draw=ImageDraw.Draw(img_pil)


size=1000
for x0,x1,y0,y1,char,_size in arr:
    print(_size)
    size=_size if _size is not None else size
    font=fontbase.font_variant(size=size)
    draw.text((x0,y0),char,(0,0,0),font)
img_2=np.array(img_pil)
# cv2.imwrite(f"out/{str(cnter)}.png",img_2)
cv2.imwrite(f"out.png",img_2)

# a,b=plt.subplots(1,2,True,True)
# b[0].imshow(img)
# b[1].imshow(img_2)
# plt.show()