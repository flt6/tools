from subprocess import Popen,PIPE
from pathlib import Path
from multiprocessing import Pool
from sys import argv
from os import environ
from matplotlib import pyplot as plt

def main(file:Path,targetPath:Path,TARGET_SIZE,MINSIZE,SINGLE):
    if SINGLE:print(f"Process {str(file)}",end="",flush=True)
    else:cnt=0
    if targetPath.exists():
        if SINGLE:
            print(f" file already exists. Check it.")
            exit()
        else:
            print(f"{targetPath} file already exists. Check it.")
            return None
    inp=file.read_bytes()
    suffix=file.suffix[1:]
    mapper={
        "jpg":"mjpeg",
        "jpeg":"mjpeg",
        "png":"image2pipe -vcodec png",
        "webp":"webp",
        "gif":"gif"
    }
    targetFmt=mapper.get(suffix,"mjpeg")
    proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:1600:bilinear\" -f {targetFmt} -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
    out,_=proc.communicate(inp)

    if SINGLE:print(".",end="",flush=True)
    else:cnt+=1
    size=1600
    delta=abs(len(out)-TARGET_SIZE)//100
    arr=[]
    while True:
        arr.append(len(out)//1024)
        lastDelta=delta
        delta=abs(len(out)-TARGET_SIZE)//100
        if delta>lastDelta:
            delta=lastDelta*3//4
        # print(delta,len(out)//1024,size)
        if delta<10:
            while len(out)>TARGET_SIZE:
                size-=10
                proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:{str(size)}:bilinear\" -f {targetFmt} -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
                out,err=proc.communicate(inp)
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
        proc=Popen(f"ffmpeg.exe -hide_banner -i - -vf \"scale=-1:{str(size)}:bilinear\" -f {targetFmt} -",stderr=PIPE,stdout=PIPE,stdin=PIPE)
        out,err=proc.communicate(inp)
        if SINGLE:print(".",end="",flush=True)
        else:cnt+=1
    # if targetFmt=="webp":
    #     proc=Popen(f"ffmpeg -hide_banner -i - {str(targetPath.resolve())}",stdin=PIPE,stderr=PIPE)
    #     proc.communicate(out)
    # else:
    print(suffix,mapper.keys())
    if suffix not in mapper.keys():
        targetPath=targetPath.with_suffix(".jpg")
    targetPath.write_bytes(out)

    plt.scatter(range(len(arr)), arr, label='arr values')
    plt.axhline(y=TARGET_SIZE//1024, color='r', linestyle='--', label=f'y={TARGET_SIZE}')
    plt.show()
    if SINGLE:print(" Success")
    else:return file,cnt

if __name__ == "__main__":
    SINGLE=False
    # argv.append("test/types")
    if len(argv)!=2:
        print(f"Usage: {__file__} dir/file")
        exit()

    TARGET_SIZE=input("Target size(k): ")
    MINSIZE=input("The minimum size allowed(k): ")
    
    config=Path(environ.get("APPDATA")+"/compressImage/config.txt")
    if TARGET_SIZE=="":
        if config.exists():
            TARGET_SIZE=config.read_text()
            print("Using last target size:",TARGET_SIZE)
        else:
            while TARGET_SIZE!="":
                print("Target size is empty and the application not been used.")
                TARGET_SIZE=input("Target size(k): ")
    config.parent.mkdir(exist_ok=True)
    config.touch(exist_ok=True)
    config.write_text(TARGET_SIZE)
    TARGET_SIZE=int(TARGET_SIZE)*1024
    
    if MINSIZE=="":
        MINSIZE=int(TARGET_SIZE*0.8)
        print("Using 80% of the target size:",MINSIZE)
    else:MINSIZE=int(MINSIZE)*1024
    
    d=Path(argv[1]).resolve()
    if d.is_file():
        main(d,d.with_stem(d.stem+"_compress"),TARGET_SIZE,MINSIZE,True)
        exit()
    files=d.glob("*")
    compressdir=(d/"compress")
    compressdir.mkdir(exist_ok=True)

    
    def callback(x):
        if x is None:
            print("Some file exists, please check.")
            p.terminate()
            exit()
        print(f"File % 20s succeeded after % 2d times try."%x)
    
    if SINGLE:
        for file in files:
            if file.suffix in [".jpg",".png",".webp",".jpeg",".gif",".tif",".tiff",".bmp"]:
                main(file,compressdir/file.name,TARGET_SIZE,MINSIZE,True)
    else:
        with Pool(16) as p:
            for file in files:
                if file.suffix in [".jpg",".png",".webp",".jpeg",".gif",".tif",".tiff",".bmp"]:
                    p.apply_async(main,(file,compressdir/file.name,TARGET_SIZE,MINSIZE,False),callback=callback)
            p.close()
            p.join()
