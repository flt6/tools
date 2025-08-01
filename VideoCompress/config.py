import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import main as main_program
from pathlib import Path

if os.environ.get("INSTALL","0") == "1":
    CONFIG_NAME = Path(os.getenv("APP_DATA", "C:/"))/"VideoCompress"/"config.json"
    CONFIG_NAME.parent.mkdir(parents=True, exist_ok=True)
else:
    CONFIG_NAME = Path(sys.path[0])/"config.json"

DEFAULT_CONFIG = {
    "save_to": "multi",
    "crf": 18,
    "codec": "h264",        # could be h264, h264_qsv, h264_nvenc … etc.
    "ffmpeg": "ffmpeg",
    "video_ext": [".mp4", ".mkv"],
    "extra": [],
    "manual": None,
    "train": False,
}

HW_SUFFIXES = ["amf", "qsv", "nvenc"]
CODECS_BASE = ["h264", "hevc"]
SAVE_METHOD = ["保存到单一Compress", "每个文件夹下建立Compress"]
preset_options = {
    "不使用":["","ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow",],
    "AMD": ["","speed","balanced","quality",],
    "Intel": ["","veryfast","faster","fast","medium","slow",],
    "NVIDIA": ["","default","slow","medium","fast","hp","hq",]
}


def config_path() -> str:
    """Return path of config file next to the executable / script."""
    if getattr(sys, "frozen", False):  # PyInstaller executable
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, CONFIG_NAME)


def load_config() -> dict:
    try:
        with open(config_path(), "r", encoding="utf-8") as fp:
            data = json.load(fp)
            if not isinstance(data, dict):
                raise ValueError("config.json root must be an object")
            return {**DEFAULT_CONFIG, **data}
    except FileNotFoundError:
        return DEFAULT_CONFIG.copy()
    except Exception as exc:
        messagebox.showwarning("FFmpeg Config", f"Invalid config.json – using defaults.\n{exc}")
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    try:
        with open(config_path(), "w", encoding="utf-8") as fp:
            json.dump(cfg, fp, ensure_ascii=False, indent=4)
    except Exception as exc:
        messagebox.showerror("配置中心", f"保存失败:\n{exc}")
    else:
        messagebox.showinfo("配置中心", "保存成功。")


class ConfigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # 设置现代化主题和统一内边距
        style = ttk.Style(self)
        style.theme_use('clam')
        self.title("配置中心")
        self.resizable(False, False)
        self.cfg = load_config()
        
        if "-preset" in self.cfg["extra"]:
            idx = self.cfg["extra"].index("-preset")
            self.preset = self.cfg["extra"][idx+1]
            self.cfg["extra"].pop(idx)
            self.cfg["extra"].pop(idx)
        else:
            self.preset = ""
        
        self._build_ui()
    # ── helper --------------------------------------------------------------
    def _grid_label(self, row: int, text: str):
        tk.Label(self, text=text, anchor="w").grid(row=row, column=0, sticky="w", pady=2, padx=4)

    def _str_var(self, key: str):
        var = tk.StringVar(value=str(self.cfg.get(key, "")))
        var.trace_add("write", lambda *_: self.cfg.__setitem__(key, var.get()))
        return var

    def _bool_var(self, key: str):
        var = tk.BooleanVar(value=bool(self.cfg.get(key)))
        var.trace_add("write", lambda *_: self.cfg.__setitem__(key, var.get()))
        return var

    def _list_var_entry(self, key: str, width: int = 28):
        """Comma-separated list entry bound to config[key]."""
        var = tk.StringVar(value=",".join(self.cfg.get(key, [])))

        def _update(*_):
            self.cfg[key] = [s.strip() for s in var.get().split(",") if s.strip()]

        var.trace_add("write", _update)
        ent = tk.Entry(self, textvariable=var, width=width)
        return ent

    # ── UI ------------------------------------------------------------------
    def _build_ui(self):
        row = 0
        padx_val = 6
        pady_val = 4
        
        self._grid_label(row, "输出方式")
        save_method = tk.StringVar()
        save_method.set(next((c for c in SAVE_METHOD if self.cfg["save_to"].startswith(c)), SAVE_METHOD[0]))
        save_method = ttk.Combobox(self, textvariable=save_method, values=SAVE_METHOD, state="readonly", width=20)
        save_method.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1
        # 编解码器
        self._grid_label(row, "编解码器 (h264 / hevc)")
        codec_base = tk.StringVar()
        codec_base.set(next((c for c in CODECS_BASE if self.cfg["codec"].startswith(c)), "h264"))
        codec_menu = ttk.Combobox(self, textvariable=codec_base, values=CODECS_BASE, state="readonly", width=10)
        codec_menu.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # 显卡品牌（硬件加速）
        self._grid_label(row, "GPU加速")
        accel = tk.StringVar()
        brand_vals = ["不使用", "NVIDIA", "AMD", "Intel"]
        def get_brand():
            codec = self.cfg["codec"]
            if codec.endswith("_nvenc"):
                return "NVIDIA"
            elif codec.endswith("_amf"):
                return "AMD"
            elif codec.endswith("_qsv"):
                return "Intel"
            return "不使用"
        accel.set(get_brand())
        accel_menu = ttk.Combobox(self, textvariable=accel, values=brand_vals, state="readonly", width=10)
        accel_menu.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # CRF或码率选择
        mode = tk.StringVar(value="crf")
        if "bitrate" in self.cfg:
            mode.set("bitrate")
        def _switch_mode():
            if mode.get() == "crf":
                bitrate_ent.configure(state="disabled")
                crf_ent.configure(state="normal")
            else:
                crf_ent.configure(state="disabled")
                bitrate_ent.configure(state="normal")
        tk.Radiobutton(self, text="使用 CRF", variable=mode, value="crf", command=_switch_mode).grid(row=row, column=0, sticky="w", padx=padx_val, pady=pady_val)
        tk.Radiobutton(self, text="使用码率", variable=mode, value="bitrate", command=_switch_mode).grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # CRF输入框，并在标签中解释参数含义
        self._grid_label(row, "CRF 值（质量常数，数值越低质量越高）")
        crf_var = self._str_var("crf")
        crf_ent = tk.Entry(self, textvariable=crf_var, width=6)
        crf_ent.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # 码率输入框 (kbit/s)
        self._grid_label(row, "码率 (例如6M, 200k)")
        bitrate_var = tk.StringVar(value=str(self.cfg.get("bitrate", "")))
        def _update_bitrate(*_):
            if mode.get() == "bitrate":
                try:
                    self.cfg["bitrate"] = bitrate_var.get().strip()
                except ValueError:
                    self.cfg.pop("bitrate", None)
        bitrate_var.trace_add("write", _update_bitrate)
        bitrate_ent = tk.Entry(self, textvariable=bitrate_var, width=8)
        bitrate_ent.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # 预设选项
        self._grid_label(row, "预设 (决定压缩的速度和质量)")
        preset_var = tk.StringVar(value=self.preset)

        def _update_preset_option(*_):
           preset_menu['values'] = preset_options[accel.get()]
           preset_menu.set("")
        def _update_preset(*_):
            print(preset_var.get())
            if self.cfg["extra"].count("-preset")>0:
                idx = self.cfg["extra"].index("-preset")
                self.cfg["extra"].pop(idx)
                self.cfg["extra"].pop(idx)
            if preset_var.get():
                self.cfg["extra"].extend(["-preset", preset_var.get()])
        preset_var.trace_add("write", _update_preset)
        accel.trace_add("write",_update_preset_option)
        preset_menu = ttk.Combobox(self, textvariable=preset_var, values=preset_options[get_brand()], state="readonly", width=10)
        preset_menu.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # ffmpeg路径
        self._grid_label(row, "ffmpeg 可执行文件")
        ffmpeg_var = self._str_var("ffmpeg")
        ffmpeg_ent = tk.Entry(self, textvariable=ffmpeg_var, width=28)
        ffmpeg_ent.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        ttk.Button(self, text="浏览", command=lambda: self._pick_ffmpeg(ffmpeg_var)).grid(row=row, column=2, padx=2, pady=pady_val)
        row += 1

        # 视频扩展名列表
        self._grid_label(row, "视频扩展名 (.x,.y)")
        self._list_var_entry("video_ext").grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # 额外参数列表
        self._grid_label(row, "额外参数列表")
        extra_entry = self._list_var_entry("extra")
        extra_entry.grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        # 手动参数列表
        self._grid_label(row, "手动参数列表")
        manual_var = tk.StringVar(value="" if self.cfg.get("manual") is None else " ".join(self.cfg["manual"]))
        def _update_manual(*_):
            txt = manual_var.get().strip()
            self.cfg["manual"] = None if not txt else txt.split()
        manual_var.trace_add("write", _update_manual)
        tk.Entry(self, textvariable=manual_var, width=28).grid(row=row, column=1, sticky="w", padx=padx_val, pady=pady_val)
        row += 1

        
        
        # 训练模式复选框
        train_var = self._bool_var("train")
        tk.Checkbutton(self, text="启用训练（实验性）", variable=train_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=padx_val, pady=pady_val)
        row += 1


        # 按钮
        ttk.Button(self, text="保存", command=lambda: self._on_save(save_method,codec_base, accel, mode)).grid(row=row, column=0, pady=8, padx=padx_val)
        ttk.Button(self, text="退出", command=self.destroy).grid(row=row, column=1, pady=8)
        _switch_mode()  # 初始启用/禁用

    # ── callbacks -----------------------------------------------------------
    def _on_save(self, save_method, codec_base_var, accel_var, mode_var):
        # 重构codec字符串，同时处理显卡品牌映射
        save_to = save_method.get()
        base = codec_base_var.get()
        brand = accel_var.get()
        brand_map = {"NVIDIA": "nvenc", "AMD": "amf", "Intel": "qsv", "不使用": ""}
        if brand != "不使用":
            self.cfg["codec"] = f"{base}_{brand_map[brand]}"
        else:
            self.cfg["codec"] = base
        # 处理码率和crf的配置
        if mode_var.get() == "crf":
            self.cfg.pop("bitrate", None)
        else:
            br = self.cfg.get("bitrate", "")
            if not (br.endswith("M") or br.endswith("k")):
                messagebox.showwarning("警告", "码率参数可能配置错误。例如：3M, 500k")
        tmp = self.cfg["extra"]
        idx = 0
        if len(tmp) == 0:idx = -1
        else:
            while True:
                if tmp[idx] == "-preset":break
                elif idx+2==len(tmp):
                    idx = -1
                    break
                else: idx+=1
        if idx!=-1:
            preset = self.cfg["extra"][idx+1]
            if preset not in preset_options[brand]:
                messagebox.showwarning("警告", "预设(preset)参数可能配置错误！")
                
        save_config(self.cfg)

    def _pick_ffmpeg(self, var):
        path = filedialog.askopenfilename(title="Select ffmpeg executable")
        if path:
            var.set(path)


def main():
    if len(sys.argv) > 1:
        main_program.main()
    else:
        app = ConfigApp()
        app.mainloop()


if __name__ == "__main__":
    main()
