from browser import document
from pickle import load
with open("File.data","rb") as f:
    d=load(f)
def run(data):
    t=document["name"].value
    ans=""
    for i in range(len(t)):
        try:
            ans += d[t[i]]+" "
        except KeyError:
            document.alert("Can't convert '%s'."%(t[i]))
    document["ans"].text=ans
document["check"].bind("click",run)
