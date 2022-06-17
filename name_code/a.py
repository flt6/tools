base=0xa0a0
with open("File.md","w",encoding="utf-8") as f:
    print("| |",end='',file=f)
    for j in range(1,94+1):
        print('%02d|'%(j,),end='',file=f)
    print(file=f)
    for j in range(1,94+2):
        print('-|',end='',file=f)
    print(file=f)
    for i in range(1,87+1):
        print("|",end='',file=f)
        if i%10==0:
            print(' |',file=f,end='')
            for j in range(1,94+1):
                print('%02d|'%(j,),end='',file=f)
            # for j in range(1,94+2):
                # print(" |",file=f,end='')
            print('',file=f)
        print('%02d'%i,file=f,end='|')
        
        for j in range(1,94+1):
            t=base+(i<<8)+j
            t=t.to_bytes(2,'big')
            # print(t)
            try:
                print(t.decode("gb2312"),end='|',file=f)
            except UnicodeDecodeError:
                print(end=' |',file=f)
        print('',file=f)