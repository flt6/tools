from sys import argv,exit
from pydub import AudioSegment,silence
from os import path,mkdir,system
from shutil import rmtree
from traceback import print_exc


def init():
    if len(argv) != 2:
        print("Usage: a.py file.mp3")
        exit(1)
    return argv[1]
    # return "新课程外研高一第32期.mp3"

def make_dir(pth:str):
    if not path.isdir(pth):
        try:
            mkdir(pth)
        except PermissionError:
            print("Could not create directory '{pth}' because of permission error.".format(pth=pth))
            exit(-1) 
    else:
        ipt=input(f"'{pth}' exists. Remove it [YES/no]: ")
        if ipt == "" or ipt == "yes":
            try:
                rmtree(pth)
            except PermissionError:
                print("Could not remove '{pth}' because of permission error.".format(pth=pth))
                exit(-1)
            mkdir(pth)
        else:
            print(f"Warning: Directory '{pth}' exists, which may influence the programm!")

def cut(file:AudioSegment,length:list[int],keep=300) -> AudioSegment:
    maxlen = len(file)
    bgn,end=length
    if bgn-keep>=0:
        bgn-=keep
    if end+keep<=maxlen:
        end+=keep
    return file[bgn:end]

def main():
    file = init()
    NAMES=["BASIC", "1-5", "Others"]
    make_dir("OUTPUT")
    for i in NAMES:
        make_dir(f"OUTPUT/{i}")
    print("Reading file ...")
    file:AudioSegment = AudioSegment.from_file(file)
    print("Detecting audio segments ...")
    arr=silence.detect_nonsilent(
        file,
        silence_thresh=-100,
        seek_step=500,
        min_silence_len=4000
    )
    print("Cutting audio segments ...")
    group=[]
    groups=[]
    
    groups.append([(cut(file,arr[0]),'info'),(cut(file,arr[1]),'example')])
    for i in range(2,2+5):
        group.append((cut(file,arr[i]),str(i-1)))
    groups.append(group)
    group=[]
    for i in range(7,len(arr)-1,2):
        group.append((cut(file,arr[i]),f"Tips_of_{(i-7)//2+6}"))
        group.append((cut(file,arr[i+1]),f"Text_{(i-7)//2+6}"))
    groups.append(group)
    for i,group in enumerate(groups):
        print(f"Saving audio segments '{NAMES[i]}' ...")
        for f,name in group:
            f.export(f"OUTPUT/{NAMES[i]}/{name}.mp3")
    print("Done!")
        

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        system("pause")
    except KeyboardInterrupt as e:
        raise e
    except Exception:
        print("An unexpected exception occurred.")
        print_exc()
