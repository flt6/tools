from getpass import getpass
from subprocess import Popen

cmd=input("SSH: ").split()
pwd=getpass()
port=cmd[2]
ip=cmd[3].replace("root@",f"root:{pwd}@")
print(ip,port)
Popen(fr'"C:\Program Files (x86)\NetSarang\Xshell 7\Xshell.exe" ssh://{ip}:{port}')
ssh=Popen(f"ssh -CNg -L 6006:127.0.0.1:6006 -p {port} {cmd[3]}")