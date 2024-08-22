from subprocess import Popen,PIPE
from pathlib import Path
from multiprocessing import Pool
from sys import argv

SINGLE=False

def main(file:Path,TARGET_SIZE,MINSIZE,compressdir):
    if SINGLE:print(f"Process {str(file)}",end="",flush=True)
    else:cnt=0
    if (compressdir/file.name).exists():
        if SINGLE:
            print(f" file already exists. Check it.")
            exit()
        else:
            print(f"{compressdir/file.name} file already exists. Check it.")
            return None
    with open(file,"rb") as f:
        inp=f.read()
    proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:1600:bilinear\" -f mjpeg -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
    out,_=proc.communicate(inp)
    if SINGLE:print(".",end="",flush=True)
    else:cnt+=1
    size=1600
    delta=abs(len(out)-TARGET_SIZE)//200
    while True:
        lastDelta=delta
        delta=abs(len(out)-TARGET_SIZE)//200
        if delta>lastDelta:
            delta=lastDelta*3//4
        if delta<10:
            while len(out)>TARGET_SIZE:
                size-=10
                proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:{str(size)}:bilinear\" -f mjpeg -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
                out,_=proc.communicate(inp)
                if SINGLE:print(".",end="",flush=True)
                else:cnt+=1
            break
        if len(out)>TARGET_SIZE:
            while size<delta:delta//=2
            size-=delta
        elif (TARGET_SIZE-len(out))>TARGET_SIZE-MINSIZE:
            assert(TARGET_SIZE-len(out))>0
            size+=delta
        else:
            break
        proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:{str(size)}:bilinear\" -f mjpeg -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
        out,_=proc.communicate(inp)
        if SINGLE:print(".",end="",flush=True)
        else:cnt+=1
    with open(compressdir/file.name,"wb") as f:
        f.write(out)
    if SINGLE:print(" Success")
    else:return file,cnt

if __name__ == "__main__":
    if len(argv)!=2:
        print(f"Usage: {__file__} dir")
        exit()
    d=Path(argv[1]).resolve()
    files=d.glob("*")
    compressdir=(d/"compress")
    compressdir.mkdir(exist_ok=True)

    TARGET_SIZE=int(input("Target size(k): "))*1024
    MINSIZE=int(input("The minimum size allowed(k): "))*1024
    
    # print("Target size:",TARGET_SIZE//1024,"k")
    # print("The minimum size allowed:",MINSIZE//1024,"k")
    def callback(x):
        if x is None:
            print("Some file exists, please check.")
            p.terminate()
            exit()
        print(f"File % 20s succeeded after % 2d times try."%x)
    
    if SINGLE:
        for file in files:
            if file.suffix in [".jpg",".png"]:
                main(file,TARGET_SIZE,MINSIZE,compressdir)
    else:
        with Pool(16) as p:
            for file in files:
                if file.suffix in [".jpg",".png"]:
                    p.apply_async(main,(file,TARGET_SIZE,MINSIZE,compressdir),callback=callback)
            p.close()
            p.join()
