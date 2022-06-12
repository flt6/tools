from req import Req
from json import dump
import pickle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase import ttfonts
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

with open("data.conf","rb") as f:
    data=pickle.load(f)
# with open("data.json","w",encoding="utf-8")as f:
#     dump(data,f)
can=canvas.Canvas("file.pdf")
pdfmetrics.registerFont(ttfonts.TTFont("st","C:\Windows\Fonts\STSONG.TTF"))
for text in data["single_box"]["hand_text"]:
    pos=text["poses"]
    can.setFont("st",(pos[2]['y']-pos[0]['y'])/4)
    t=('#####'.join(text["texts"]))
    can.drawString(*text["poses"][0].values(),t)
can.showPage()
can.save()