from flask import Flask, render_template, request, redirect, url_for
import random
from json import loads,dumps
from pathlib import Path
from os import remove
from enum import Enum

class Status(Enum):
    NoConfig=0
    Assign=1
    Assigned=2

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 全局存储任务配置和分配结果
# task_config = {}
# user_intentions = {}
# totTas=0
# totInt=0
# assignment_result = {}
# status = Status.NoConfig

cfgFile=Path("config.json")
if cfgFile.exists():
    cfg:dict=loads(cfgFile.read_text())
else:
    cfg=dict()

task_config:dict=cfg.get("task_config",{})
user_intentions:dict = cfg.get("user_intentions",{})
assignment_result:dict = cfg.get("assignment_result",{})
totTas = sum(task_config.values())
totInt = sum(map(len,user_intentions.values()))
status=Status(cfg.get("status",0))

def save():
    cfg={
        "task_config":task_config,
        "user_intentions":user_intentions,
        "status":status.value
    }
    cfgFile.write_text(dumps(cfg))

@app.route("/config", methods=["GET", "POST"])
def config():
    global task_config,user_intentions,totTas,status
    if request.method == "POST":
        # 从表单获取任务和人数配置
        tasks = request.form.getlist("task")
        counts = request.form.getlist("count")
        task_config = {task: int(count) for task, count in zip(tasks, counts)}
        user_intentions = {task: [] for task in tasks}
        totTas=sum(task_config.values())
        status = Status.Assign
        save()
        return redirect(url_for("user_page"))
    if status==Status.NoConfig:
        return render_template("config.html")
    elif status==Status.Assign:
        task_status = []
        for task, max_count in task_config.items():
            current_count = len(user_intentions[task])
            status_color = "red" if current_count > max_count else "green" if current_count < max_count else "white"
            task_status.append({
                "task": task,
                "max_count": max_count,
                "current_count": current_count,
                "status_color": status_color,
                "users": user_intentions[task]
            })
        return render_template("config_view.html", task_status=task_status)
    else:
        return redirect(url_for("result"))

@app.route("/")
def index():
    if status == Status.Assigned:
        return redirect(url_for("result"))
    elif status == Status.Assign:
        return redirect(url_for("user_page"))
    else:
        return error("未配置","任务信息未配置，请联系管理员")

def error(title,content):
    return render_template("error.html", title=title, content=content)

@app.route("/user", methods=["GET", "POST"])
def user_page():
    global user_intentions,totInt
    if status != Status.Assign:
        return redirect(url_for("index"))
    if request.method == "POST":
        # 用户提交意向
        name = request.form["name"]
        intention = request.form["intention"]
        user_intentions[intention].append(name)
        totInt+=1
        save()
        if totInt==totTas:
            assign()
        return redirect(url_for("result"))
    return render_template("user.html", tasks=task_config,init=list(task_config.values())[0])


# @app.route("/assign", methods=["GET"])
def assign():
    global assignment_result,status
    # 任务总人数计算
    task_slots = {task: [] for task in task_config}

    # 分配意向
    unassigned_users = []
    notFull = {}
    for task,maxcnt in task_config.items():
        cnt=len(user_intentions[task])
        if cnt>maxcnt:
            random.shuffle(user_intentions[task])
            unassigned_users.extend(user_intentions[task][:(maxcnt-cnt)])
            task_slots[task]=user_intentions[task][(maxcnt-cnt):]
        else:
            task_slots[task]=user_intentions[task]
            if cnt<maxcnt: notFull.update({task:maxcnt-cnt})
    
    offset=0
    for task,need in notFull.items():
        task_slots[task].extend(unassigned_users[offset:(need+offset)])
        offset+=need

    assignment_result = task_slots
    status=Status.Assigned
    remove(cfgFile)


@app.route("/result", methods=["GET"])
def result():
    if status==Status.NoConfig:
        return error("无法查看结果","分配尚未开始，请联系管理员。")
    elif status==Status.Assign:
        return error("无法查看结果","分配尚未结束，请等待所有人选择后查看。")

    return render_template("result.html", assignment_result=assignment_result)


if __name__ == "__main__":
    app.run(debug=True)
