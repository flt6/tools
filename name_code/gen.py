from pickle import dump
d=[]
base=0xa0a0
for i in range(1,87+1):
    for j in range(1,94+1):
        t=base+(i<<8)+j
        t=t.to_bytes(2,'big')
        try:
            d.append(("%02d%02d"%(i,j),t.decode("gb2312")))
        except UnicodeDecodeError:
            pass
d=dict(d)
with open("a.dat","wb") as f:
    dump(d,f)
