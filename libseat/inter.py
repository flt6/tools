# app.py  ── 运行：python app.py
import re, threading, datetime as dt
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "secret"

# ---------- ❶ 你要周期执行的业务函数 ----------
def my_task():
    print(f"[{dt.datetime.now():%F %T}] 🎉 my_task 被调用")

# ---------- ❷ 将 “1h / 30min / 45s” 解析为秒 ----------
def parse_interval(expr: str) -> int:
    m = re.match(r"^\s*(\d+)\s*(h|hr|hour|m|min|minute|s|sec)\s*$", expr, re.I)
    if not m:
        raise ValueError("格式不正确——示例: 1h、30min、45s")
    n, unit = int(m[1]), m[2].lower()
    return n * 3600 if unit.startswith("h") else n * 60 if unit.startswith("m") else n

# ---------- ❸ 简易调度器 (Thread + Event) ----------
class LoopWorker(threading.Thread):
    def __init__(self, interval_s: int, fn):
        super().__init__(daemon=True)
        self.interval_s = interval_s
        self.fn = fn
        self._stop = threading.Event()

    def cancel(self):
        self._stop.set()

    def run(self):
        while not self._stop.wait(self.interval_s):
            try:
                self.fn()
            except Exception as e:
                print("任务执行出错:", e)

worker: LoopWorker | None = None   # 全局保存当前线程
current_expr: str = ""   # 全局保存当前表达式

# ---------- ❹ Tailwind + Alpine 渲染 ----------
PAGE = """
<!doctype html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <title>周期设置</title>
  <script src="https://cdn.tailwindcss.com/3.4.0"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <div class="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl space-y-6">    <header class="flex justify-between items-center">
      <h1 class="text-2xl font-semibold text-gray-800">周期设置</h1>
    </header>    {% with msgs = get_flashed_messages(with_categories=true) %}
      {% if msgs %}
        {% for cat, msg in msgs %}
          <div class="px-4 py-2 rounded-lg text-sm {{ 'bg-green-100 text-green-800' if cat=='success' else 'bg-red-100 text-red-800' }}">
            <span>{{ msg }}</span>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="post" class="space-y-4">
      <input name="interval" required placeholder="例：1h / 30min / 45s"
             class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2
                    focus:ring-indigo-400 focus:outline-none"/>
      <button class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium">
        设置周期
      </button>
    </form>

    <p class="text-xs text-gray-500">
      当前任务：<br>
      {% if worker %}
        每 {{current_expr}} 触发一次（刷新页面查看最新状态）
      {% else %}
        未设置
      {% endif %}
    </p>
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    global worker, current_expr
    if request.method == "POST":
        expr = request.form["interval"].strip()
        try:
            if expr == "0":
                # 如果输入为 "0"，则取消当前任务
                if worker:
                    worker.cancel()
                    worker = None
                    current_expr = ""
                    flash("✅ 已取消定时任务", "success")
                return redirect(url_for("index"))
            sec = parse_interval(expr)
            # 取消旧线程
            if worker:
                worker.cancel()
            # 启动新线程
            worker = LoopWorker(sec, my_task)
            worker.start()
            current_expr = expr  # 保存表达式
            print(expr)
            flash(f"✅ 已设置：每 {expr} 运行一次 my_task()", "success")
        except Exception as e:
            flash(f"❌ {e}", "error")
        return redirect(url_for("index"))

    return render_template_string(PAGE, worker=worker, current_expr=current_expr)

if __name__ == "__main__":
    app.run(debug=True)
