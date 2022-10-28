from sys import argv
from os.path import isfile, isdir,abspath
from os import mkdir
from chardet import detect
from colorama import init,Fore
HELP = '''
Usage: recode.py <options>/<filename(s)>
'''
TARGET = 'utf-8'
OUTDIR = "Output"


def main(files):
    if not isdir(OUTDIR):
        mkdir(OUTDIR)

    for file in files:
        path = abspath(file)
        path = path.replace("\\", "/")
        path = path.split('/')
        path = '/'.join(path[:-1])+"/"+OUTDIR+"/"+path[-1]
        if isfile(path):
            print(Fore.YELLOW+f"WARN: File '{path} exists. Ignore.")
            continue
        recode(file,path)


def recode(file,path):
    try:
        with open(file, 'rb') as f:
            tem = f.read()
    except Exception as e:
        print(Fore.RED+f"ERROR: Can't open file '{file}'")
        return
    ret = detect(tem)
    if ret["encoding"] is None:
        print(Fore.RED+"ERROR: Cannot detect encoding of `%s`" % file)
        return
        
    with open(file, 'r',encoding=ret["encoding"]) as f:
        tem = f.read()

    if ret['confidence'] < 0.8:
        print(Fore.YELLOW+"WARN: File `%s` confidence is lower than 0.8. Recognized as `%s`."%(file,ret["encoding"]))

    with open(path, 'w', encoding=TARGET) as f:
        f.write(tem)
    print(Fore.LIGHTBLUE_EX+"INFO: Success for `%s` with confidence %0.1f%%"%(file,ret["confidence"]*100))


if __name__ == '__main__':
    init(autoreset=True)
    if len(argv) == 1:
        print(HELP)
    else:
        main(argv[1:])
        print("------------------------")
    input("Press enter to exit")
