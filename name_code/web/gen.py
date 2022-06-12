from pickle import dump
opt={}
base=0xa0a0
for i in range(1,87+1):
    for j in range(1,94+1):
        t=base+(i<<8)+j
        t=t.to_bytes(2,'big')
        # print(t)
        try:
            opt[t.decode("gb2312")]='%02d%02d'%(i,j)
        except UnicodeDecodeError:
            pass

print(opt["啊"])
with open("File.data","wb") as f:
    dump(opt,f)