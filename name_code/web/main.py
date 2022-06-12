t=input("Name: ").encode("GB2312")
for i in range(0,len(t),2):
    print("%02d%02d"%(t[i]-0xA0,t[i+1]-0xA0),end=" ")