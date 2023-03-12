from subprocess import Popen,PIPE
from os import listdir
from os.path import isdir

pool:dict[str,Popen] = dict()
names_code:list[str] = []
names_alt:list[str] = []
vid:list[str] = []
paths = listdir()
while len(paths)!=0:
    for path in paths:
        paths.pop(paths.index(path))
        if isdir(path):
            paths.extend([path+"/"+i for i in listdir(path)])
        if "tmp" in path:
            continue
        if path[-3:] in ["mp4", "flv"]:
            vid.append(path)

print(vid)
for path in vid:
    names_code.append(path)
    cmd = ['ffmpeg',
        # '-hwaccel',
        # 'cuda',
        # '-hwaccel_output_format',
        # 'cuda',
        '-i',
        path,
        # '-c:v',
        # 'h264_nvenc',
        '-y',
        'tmp_'+path
    ]
    pool.update({path:Popen(cmd,stderr=open(path+"_ffmpeg.log","w",encoding="utf-8"))})
    while len(names_code)>3:
        for name in names_code.copy(): # To avoid the infulence of names_code modification
            if pool[name].poll() is not None:
                ret = pool[name].poll()
                print(ret)
                if ret != 0:
                    print(f"'{name}' error")
                elif pool[name].args[0] == "ffmpeg":
                    tmp = 'tmp_'+name
                    names_alt.append(tmp)
                    cmd = [
                        "auto-editor",
                        "-mcut",
                        "1",
                        "-o",
                        "opt/"+name,
                        tmp
                    ]
                    pool.update({tmp:Popen(cmd,stderr=open(name+"_auto.log","w",encoding="utf-8"))})
                    names_code.append(tmp)
                elif pool[name].args[0] == "auto-editor":
                    print(f"'{name}' success")
            pool.pop(name)
            names_code.pop(names_code.index(name))

print(names_code,len(names_code),len(names_code)>0)
while len(names_code)>0:
    for name in names_code.copy(): # To avoid the infulence of names_code modification
        if pool[name].poll() is not None:
            ret = pool[name].poll()
            if ret != 0:
                print(f"'{name}' error")
            elif pool[name].args[0] == "ffmpeg":
                tmp = 'tmp_'+name
                names_alt.append(tmp)
                cmd = [
                    "auto-editor",
                    "-mcut",
                    "1",
                    "-o",
                    "opt/"+name,
                    tmp
                ]
                pool.update({tmp:Popen(cmd,stdout=open(name+"_auto.log","w",encoding="utf-8"))})
                names_code.append(tmp)
            elif pool[name].args[0] == "auto-editor":
                print(f"'{name}' success")
            pool.pop(name)
            names_code.pop(names_code.index(name))