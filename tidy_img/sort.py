import re
import shutil
from pathlib import Path
from hashlib import sha256

d= Path(".").absolute()

samefiles:list[Path]=[]
cnt={}
i=0

for file in d.glob("**/*"):
    if not file.is_file():continue
    i+=1
    result = re.search("(IMG|VID)_(\d{4})(\d{2})(\d{2})_(\d{6})(_.+)?\.(jpg|mp4)",file.name)
    if not result:continue
    if re.search(r"[\\\/]?20\d{2}[\\\/]",str(file.relative_to(d))) is not None:continue
    if result.group(2) in cnt.keys():
        cnt[result.group(2)]+=1
    else:
        cnt[result.group(2)]=1
    if i&7==0:
        for key,val in cnt.items():
            print(f"{key}: {val}")
        print()
    target_dir=d/result.group(2)
    target_dir.mkdir(exist_ok=True)
    target =target_dir/file.name
    if target.exists():
        with open(file,"rb") as f:
            fileHash=sha256(f.read())
        if target.stat().st_size == file.stat().st_size:
            with open(target,"rb") as f:
                targetHash=sha256(f.read())
            if fileHash.hexdigest()==targetHash.hexdigest():
                samefiles.append(file)
                continue
        target_dir=d/"conflict"/result.group(2)
        target_dir.mkdir(parents=True,exist_ok=True)
        target =target_dir/(file.with_stem(file.name+"_"+fileHash.hexdigest()[:5]).name)
    shutil.move(file,target)
 
if len(samefiles)!=0:
    print("Detected same files: \n","\n".join([str(file) for file in samefiles]))
    ipt=input("Delete Y/n: ")
    if ipt ==  "n":
        exit()
    for file in samefiles:
        file.unlink()