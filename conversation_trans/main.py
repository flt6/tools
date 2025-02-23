from json import loads
from typing import Literal
from re import sub

data = loads(r'''''')


class Msg:
    id:int
    par:int
    role:Literal["SYSTEM","USER","ASSISTANT"]
    thinking_time:float
    thinking_content:str
    content:str
    time:float
    
    def __init__(self,msg:dict):
        if msg is None:
            self.time=0
            return
        self.id=msg["message_id"]
        self.par=msg["parent_id"]
        self.role=msg["role"]
        self.thinking_time=sub(r"\\[\(\)]","$",msg["thinking_elapsed_secs"])
        self.thinking_content=sub(r"\\[\[\]]","$$",msg["thinking_content"])
        self.content=msg["content"]
        self.time=msg["inserted_at"]
        
        if self.par==None:self.par=0

inp = data["data"]["biz_data"]["chat_messages"]
msgs:list[Msg]=[Msg(None)]

child:list[list[Msg]]=[[] for _ in range(len(inp)+1)]

new=Msg(None)

for smsg in inp:
    msg = Msg(smsg)
    msgs.append(msg)
    child[msg.par].append(msg)
    if msg.time>new.time:
        new=msg

que=[0]
path=[]
def dfs(x:int):
    path.append(x)
    if new.id==x:
        return True
    for msg in child[x]:
        if dfs(msg.id): return True
    path.pop()


if not dfs(0):
    raise RuntimeError("Cannot find latest node in tree.")

path.pop(0)
title = data['data']['biz_data']['chat_session']['title']
out=[f"# {title}"]
for i in path:
    resp=[]
    msg:Msg = msgs[i]
    resp.append(f"## {msg.role.capitalize()}")
    if msg.thinking_time is not None:
        resp.append(f"> thinking for {msg.thinking_time}s")
        resp.extend(map("> {}".format,msg.thinking_content.splitlines()))
    resp.append(msg.content)
    out.append("\n".join(resp))

try:
    with open(f"{title}.md","w",encoding="utf-8") as f:
        f.write("\n\n".join(out))
except IOError or OSError:
    with open(f"out.md","w",encoding="utf-8") as f:
        f.write("\n\n".join(out))
    