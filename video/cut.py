from sys import argv
from subprocess import run
from os import system

if len(argv) != 2:
    print("Usage: <file>")
    exit(1)
file = argv[1]
tem=file.split(".")
name = ".".join(tem[:-1])
o = tem[-1]
bgn = input("bgn: ")
if bgn=="":
    bgn="0"
to = input("to: ")
cmd = [
    r'E:\green\ffmpeg\bin\ffmpeg.exe',
    '-i',
    file,
    '-ss',
    bgn,
    '-to',
    to,
    '-c',
    'copy',
    name+"_cut."+o
]
print(cmd)
# run("pause")
ret = run(cmd)
print("ffmpeg finished with code",ret.returncode)
system("pause")