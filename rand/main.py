from random import randint

bgn,end=[int(i) for i in input("Option: Input random area(like 21-43): ").split("-")]
obj=int(input("Option: Amount: "))
repeat=input("Option: Allow repeat:\nAccept: T(true) (defalt), F(false)\n").lower()
if repeat == "":
    repeat=True
else:
    if repeat in ["t","true"]:
        repeat=True
    elif repeat in ["f","false"]:
        repeat=False
    else:
        input("Unsupported option.")
l=[]
if repeat:
    l=[randint(bgn,end) for i in range(obj)]
else:
    i=0
    while len(l)<obj and i<500:
        t=randint(bgn,end)
        i+=1
        if t not in l:
            l.append(t)

print(l)
for i in l[1:]:
    print(randint(bgn,end),end=", ")
print(l[0])