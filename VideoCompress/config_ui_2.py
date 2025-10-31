# -*- coding: utf-8 -*-
"""
Fluent Design 配置界面（PySide6 + QFluentWidgets）

功能要点：
- 拆分「通用」与「高级」两页，符合需求
- 内置 GPU 模板：CPU/libx264、NVIDIA(NVENC/cuda)、Intel(QSV)、AMD(AMF)
- 与 Pydantic Config 对接：即时校验，错误信息以 InfoBar 呈现
- 生成/预览 ffmpeg 命令；可对单文件执行（subprocess.run）
- 可导入/导出配置（JSON）

依赖：
    pip install PySide6 qfluentwidgets pydantic

注意：
- 按需在同目录准备 main.py，导出：
    from pydantic import BaseModel
    class Config(BaseModel): ...
    def get_cmd(video_path: str | Path, output_file: str | Path) -> list[str]: ...
- 本 UI 会在运行前，把实例化后的配置对象挂到 main 模块：`main.config = cfg`
  若你的 get_cmd 内部使用全局 config，将能读到该对象。
"""

from __future__ import annotations
import json
import os
import re
import sys
import subprocess
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit
)

# QFluentWidgets
from qfluentwidgets import (
    FluentWindow, setTheme, Theme, setThemeColor, FluentIcon,
    NavigationItemPosition, PrimaryPushButton, PushButton, LineEdit,
    ComboBox, SpinBox, SwitchButton, InfoBar, InfoBarPosition,
    CardWidget, NavigationPushButton
)

# Pydantic
from pydantic import ValidationError

# ---- 导入业务对象 -----------------------------------------------------------
try:
    import main as main_module  # 用于挂载 config 实例
    from main import Config, get_cmd  # 直接调用用户提供的方法
except Exception as e:  # 允许先运行 UI 草拟界面，不阻断
    main_module = None
    Config = None  # type: ignore
    get_cmd = None  # type: ignore
    print("[警告] 无法从 main 导入 Config / get_cmd：", e)


# --------------------------- 工具函数 ----------------------------------------

def show_error(parent: QWidget, title: str, message: str):
    InfoBar.error(
        title=title,
        content=message,
        orient=Qt.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=5000,
        parent=parent,
    )


def show_success(parent: QWidget, title: str, message: str):
    InfoBar.success(
        title=title,
        content=message,
        orient=Qt.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=3500,
        parent=parent,
    )


# --------------------------- GPU 模板 ----------------------------------------
GPU_TEMPLATES = {
    "CPU (libx264)": {
        "hwaccel": None,
        "codec": "libx264",
        "extra": ["-preset", "slow"],
        "crf": 23,
        "bitrate": None,
    },
    "NVIDIA (NVENC/cuda)": {
        "hwaccel": "cuda",
        "codec": "h264_nvenc",
        "extra": ["-preset", "p6", "-rc", "vbr"],
        "crf": None,
        "bitrate": "5M",
    },
    "Intel (QSV)": {
        "hwaccel": "qsv",
        "codec": "h264_qsv",
        "extra": ["-preset", "balanced"],
        "crf": None,
        "bitrate": "5M",
    },
    "AMD (AMF)": {
        "hwaccel": "amf",
        "codec": "h264_amf",
        "extra": ["-quality", "balanced"],
        "crf": None,
        "bitrate": "5M",
    },
}

SAVE_TO_OPTIONS = ["single", "multi"]
HWACCEL_OPTIONS: list[Optional[str]] = [None, "cuda", "qsv", "amf"]


# --------------------------- 卡片基础 ----------------------------------------
class GroupCard(CardWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumWidth(720)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(16, 12, 16, 16)
        t = QLabel(f"<b>{title}</b>")
        t.setProperty("cssClass", "cardTitle")
        s = QLabel(subtitle)
        s.setProperty("cssClass", "cardSubTitle")
        s.setStyleSheet("color: rgba(0,0,0,0.55);")
        self.v.addWidget(t)
        if subtitle:
            self.v.addWidget(s)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self.v.addLayout(self.body)

    def add_row(self, label: str, widget: QWidget):
        row = QHBoxLayout()
        lab = QLabel(label)
        lab.setMinimumWidth(150)
        row.addWidget(lab)
        row.addWidget(widget, 1)
        self.body.addLayout(row)


# --------------------------- 通用设置页 --------------------------------------
class GeneralPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # --- I/O 区 ---
        io_card = GroupCard("输入/输出", "选择要压缩的视频与输出文件")
        self.input_edit = LineEdit(self)
        self.input_edit.setPlaceholderText("选择输入视频文件... (.mp4/.mkv 等)")
        btn_in = PrimaryPushButton("选择文件")
        btn_in.clicked.connect(self._pick_input)
        io_row = QHBoxLayout()
        io_row.addWidget(self.input_edit, 1)
        io_row.addWidget(btn_in)

        self.output_edit = LineEdit(self)
        self.output_edit.setPlaceholderText("选择输出文件路径，例如：/path/compressed.mp4")
        btn_out = PushButton("选择输出")
        btn_out.clicked.connect(self._pick_output)
        oo_row = QHBoxLayout()
        oo_row.addWidget(self.output_edit, 1)
        oo_row.addWidget(btn_out)

        io_card.body.addLayout(io_row)
        io_card.body.addLayout(oo_row)

        # --- 基础编码参数 ---
        base_card = GroupCard("基础编码", "最常用的编码参数")

        self.save_to_combo = ComboBox()
        self.save_to_combo.addItems(SAVE_TO_OPTIONS)
        base_card.add_row("保存方式(save_to)", self.save_to_combo)

        self.codec_combo = ComboBox()
        self.codec_combo.addItems(["h264", "libx264", "h264_nvenc", "h264_qsv", "h264_amf", "hevc", "hevc_nvenc", "hevc_qsv", "hevc_amf"])
        base_card.add_row("编码器(codec)", self.codec_combo)

        self.hwaccel_combo = ComboBox()
        self.hwaccel_combo.addItems(["(无)", "cuda", "qsv", "amf"])
        base_card.add_row("GPU 加速(hwaccel)", self.hwaccel_combo)

        self.resolution_edit = LineEdit()
        self.resolution_edit.setPlaceholderText("如 1920:1080 或 -1:1080，留空为不缩放")
        base_card.add_row("分辨率(resolution)", self.resolution_edit)

        self.fps_spin = SpinBox()
        self.fps_spin.setRange(0, 999)
        self.fps_spin.setValue(30)
        base_card.add_row("帧率(fps)", self.fps_spin)

        self.video_ext_edit = LineEdit()
        self.video_ext_edit.setText(".mp4,.mkv")
        base_card.add_row("视频后缀(video_ext)", self.video_ext_edit)

        self.compress_dir_edit = LineEdit()
        self.compress_dir_edit.setText("compress")
        base_card.add_row("压缩目录名(compress_dir_name)", self.compress_dir_edit)

        self.disable_hw_switch = SwitchButton("失败时禁用硬件加速(disable_hwaccel_when_fail)")
        self.disable_hw_switch.setChecked(True)
        base_card.body.addWidget(self.disable_hw_switch)

        # --- 模板 ---
        tpl_card = GroupCard("GPU 模板", "一键应用推荐参数（会覆盖 codec/hwaccel/crf/bitrate/extra）")
        self.tpl_combo = ComboBox()
        self.tpl_combo.addItems(list(GPU_TEMPLATES.keys()))
        btn_apply_tpl = PrimaryPushButton("应用模板")
        btn_apply_tpl.clicked.connect(self.apply_template)
        row_tpl = QHBoxLayout()
        row_tpl.addWidget(self.tpl_combo, 1)
        row_tpl.addWidget(btn_apply_tpl)
        tpl_card.body.addLayout(row_tpl)

        # --- 运行/预览 ---
        run_card = GroupCard("执行", "根据当前配置生成并运行 ffmpeg 命令")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        btn_preview = PushButton("生成命令预览")
        btn_preview.clicked.connect(self.on_preview)
        btn_run = PrimaryPushButton("运行压缩 (subprocess.run)")
        btn_run.clicked.connect(self.on_run)
        rrow = QHBoxLayout()
        rrow.addWidget(btn_preview)
        rrow.addWidget(btn_run)
        run_card.body.addWidget(self.preview_text)
        run_card.body.addLayout(rrow)

        # 排版
        layout.addWidget(io_card)
        layout.addWidget(base_card)
        layout.addWidget(tpl_card)
        layout.addWidget(run_card)
        layout.addStretch(1)

        # 高级区联动：由 AdvancedPage 控制
        self.link_advanced: Optional[AdvancedPage] = None

    # ----- 文件选择 -----
    def _pick_input(self):
        fn, _ = QFileDialog.getOpenFileName(self, "选择输入视频", "", "视频文件 (*.mp4 *.mkv *.mov *.avi *.*)")
        if fn:
            self.input_edit.setText(fn)

    def _pick_output(self):
        fn, _ = QFileDialog.getSaveFileName(self, "选择输出文件", "compressed.mp4", "视频文件 (*.mp4 *.mkv)")
        if fn:
            self.output_edit.setText(fn)

    # ----- 模板应用 -----
    def apply_template(self):
        name = self.tpl_combo.currentText()
        t = GPU_TEMPLATES.get(name, {})
        # 覆盖通用字段
        codec = t.get("codec")
        if codec:
            self.codec_combo.setCurrentText(codec)
        hw = t.get("hwaccel")
        if hw is None:
            self.hwaccel_combo.setCurrentIndex(0)
        else:
            self.hwaccel_combo.setCurrentText(str(hw))
        # 覆盖高级字段（若可用）
        if self.link_advanced:
            self.link_advanced.apply_template_from_general(t)
        show_success(self, "已应用模板", f"{name} 参数已填充")

    # ----- 组装配置 -----
    def _collect_config_payload(self) -> dict:
        # CRF / bitrate 值来自高级区
        adv = self.link_advanced
        crf_val = adv.crf_spin.value() if adv else None
        if adv and adv.mode_combo.currentText() == "CRF 模式":
            bitrate_val = None
        else:
            bitrate_val = adv.bitrate_edit.text().strip() or None

        # hwaccel
        _hw_text = self.hwaccel_combo.currentText()
        hwaccel_val = None if _hw_text == "(无)" else _hw_text

        # video_ext 解析
        exts = [x.strip() for x in self.video_ext_edit.text().split(',') if x.strip()]

        payload = {
            "save_to": self.save_to_combo.currentText(),
            "crf": crf_val if (adv and adv.mode_combo.currentText() == "CRF 模式") else None,
            "bitrate": bitrate_val if (adv and adv.mode_combo.currentText() == "比特率模式") else None,
            "codec": self.codec_combo.currentText(),
            "hwaccel": hwaccel_val,
            "extra": adv.parse_list_field(adv.extra_edit.toPlainText()) if adv else None,
            "ffmpeg": adv.ffmpeg_edit.text().strip() if adv else "ffmpeg",
            "ffprobe": adv.ffprobe_edit.text().strip() if adv else "ffprobe",
            "manual": adv.parse_list_field(adv.manual_edit.toPlainText()) if (adv and adv.manual_switch.isChecked()) else None,
            "video_ext": exts or [".mp4", ".mkv"],
            "compress_dir_name": self.compress_dir_edit.text().strip() or "compress",
            "resolution": self.resolution_edit.text().strip() or None,
            "fps": self.fps_spin.value(),
            "test_video_resolution": adv.test_res_edit.text().strip() if adv else "1920x1080",
            "test_video_fps": adv.test_fps_spin.value() if adv else 30,
            "test_video_input": adv.test_in_edit.text().strip() if adv else "compress_video_test.mp4",
            "test_video_output": adv.test_out_edit.text().strip() if adv else "compressed_video_test.mp4",
            "disable_hwaccel_when_fail": self.disable_hw_switch.isChecked(),
        }
        return payload

    def build_config(self) -> Config:
        if Config is None:
            raise RuntimeError("未能导入 Config。请确认 main.py 可用且在同目录。")
        payload = self._collect_config_payload()
        try:
            cfg = Config(**payload)
        except ValidationError as e:
            show_error(self, "配置校验失败", str(e))
            raise
        return cfg

    # ----- 预览/运行 -----
    def on_preview(self):
        if get_cmd is None:
            show_error(self, "缺少 get_cmd", "未能导入 get_cmd，请检查 main.py")
            return
        in_path = self.input_edit.text().strip()
        out_path = self.output_edit.text().strip()
        if not in_path or not out_path:
            show_error(self, "缺少路径", "请先选择输入与输出文件")
            return
        try:
            cfg = self.build_config()
            if main_module is not None:
                setattr(main_module, "config", cfg)  # 挂载到 main 供 get_cmd 读取
            cmd = get_cmd(in_path, out_path)
            self.preview_text.setPlainText(" ".join([repr(c) if " " in c else c for c in cmd]))
            show_success(self, "命令已生成", "如需执行请点击运行")
        except Exception as e:
            show_error(self, "生成失败", str(e))

    def on_run(self):
        if get_cmd is None:
            show_error(self, "缺少 get_cmd", "未能导入 get_cmd，请检查 main.py")
            return
        in_path = self.input_edit.text().strip()
        out_path = self.output_edit.text().strip()
        if not in_path or not out_path:
            show_error(self, "缺少路径", "请先选择输入与输出文件")
            return
        try:
            cfg = self.build_config()
            if main_module is not None:
                setattr(main_module, "config", cfg)
            cmd = get_cmd(in_path, out_path)
            # 使用 subprocess.run 执行
            completed = subprocess.run(cmd, capture_output=True, text=True)
            log = (completed.stdout or "") + "\n" + (completed.stderr or "")
            self.preview_text.setPlainText(log)
            if completed.returncode == 0:
                show_success(self, "执行成功", "视频压缩完成")
            else:
                show_error(self, "执行失败", f"返回码 {completed.returncode}")
        except Exception as e:
            show_error(self, "执行异常", str(e))


# --------------------------- 高级设置页 --------------------------------------
class AdvancedPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # 模式切换：CRF / Bitrate 互斥
        mode_card = GroupCard("编码模式", "CRF 与 比特率 二选一")
        self.mode_combo = ComboBox()
        self.mode_combo.addItems(["CRF 模式", "比特率模式"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_card.add_row("选择模式", self.mode_combo)

        self.crf_spin = SpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        mode_card.add_row("CRF 值(0-51)", self.crf_spin)

        self.bitrate_edit = LineEdit()
        self.bitrate_edit.setPlaceholderText("如 1000k / 2.5M / 1500B")
        mode_card.add_row("比特率", self.bitrate_edit)

        # 其它高级参数
        adv_card = GroupCard("高级参数", "额外 ffmpeg 参数 / 手动命令 / 可执行路径")

        self.extra_edit = QTextEdit()
        self.extra_edit.setPlaceholderText("每行一个参数；例如：\n-preset\np6\n-rc\nvbr")
        adv_card.add_row("额外(extra)", self.extra_edit)

        self.manual_switch = SwitchButton("使用手动命令 (manual)")
        self.manual_switch.setChecked(False)
        adv_card.body.addWidget(self.manual_switch)

        self.manual_edit = QTextEdit()
        self.manual_edit.setPlaceholderText("每行一个参数（会插入到 ffmpeg -i {input} {manual} {output} 中）")
        self.manual_edit.setEnabled(False)
        self.manual_switch.checkedChanged.connect(lambda c: self.manual_edit.setEnabled(c))
        adv_card.body.addWidget(self.manual_edit)

        self.ffmpeg_edit = LineEdit()
        self.ffmpeg_edit.setText("ffmpeg")
        adv_card.add_row("ffmpeg 路径", self.ffmpeg_edit)
        self.ffprobe_edit = LineEdit()
        self.ffprobe_edit.setText("ffprobe")
        adv_card.add_row("ffprobe 路径", self.ffprobe_edit)

        # 测试参数
        test_card = GroupCard("测试", "用于快速验证配置是否能跑通")
        self.test_res_edit = LineEdit(); self.test_res_edit.setText("1920x1080")
        self.test_fps_spin = SpinBox(); self.test_fps_spin.setRange(0, 999); self.test_fps_spin.setValue(30)
        self.test_in_edit = LineEdit(); self.test_in_edit.setText("compress_video_test.mp4")
        self.test_out_edit = LineEdit(); self.test_out_edit.setText("compressed_video_test.mp4")
        test_card.add_row("测试分辨率", self.test_res_edit)
        test_card.add_row("测试 FPS", self.test_fps_spin)
        test_card.add_row("测试输入文件名", self.test_in_edit)
        test_card.add_row("测试输出文件名", self.test_out_edit)
        
        # backup_card = GroupCard("备份配置", "导入导出当前配置")

        layout.addWidget(mode_card)
        layout.addWidget(adv_card)
        layout.addWidget(test_card)
        layout.addStretch(1)

        self._on_mode_changed(0)

    def _on_mode_changed(self, idx: int):
        is_crf = (idx == 0)
        self.crf_spin.setEnabled(is_crf)
        self.bitrate_edit.setEnabled(not is_crf)

    # 解析多行 -> list[str]
    @staticmethod
    def parse_list_field(text: str) -> Optional[list[str]]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines or None

    # 从通用模板带入高级字段
    def apply_template_from_general(self, tpl: dict):
        if tpl.get("crf") is not None:
            self.mode_combo.setCurrentText("CRF 模式")
            self.crf_spin.setValue(int(tpl["crf"]))
            self.bitrate_edit.clear()
        else:
            self.mode_combo.setCurrentText("比特率模式")
            self.bitrate_edit.setText(str(tpl.get("bitrate", "5M")))
        self.extra_edit.setPlainText("\n".join(tpl.get("extra", [])))


# --------------------------- 主窗体 ------------------------------------------
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频压缩配置 - Fluent UI")
        self.resize(980, 720)

        # 主题与主色
        setTheme(Theme.AUTO)
        setThemeColor("#2563eb")  # Tailwind 蓝-600

        # 页面
        self.general = GeneralPage()
        self.general.setObjectName("general_page")
        self.advanced = AdvancedPage()
        self.advanced.setObjectName("advanced_page")
        self.general.link_advanced = self.advanced

        # 导航
        self.addSubInterface(self.general, FluentIcon.VIDEO, "通用 Config")
        self.addSubInterface(self.advanced, FluentIcon.SETTING, "高级 Config")

        # 顶部右侧：操作按钮
        # self.navigationInterface.addWidget(  # type: ignore
        #     routeKey="spacer",
        #     widget=QLabel(""),
        #     onClick=None,
        #     position=NavigationItemPosition.TOP
        # )

        # 导入/导出配置
        export_btn = NavigationPushButton(FluentIcon.SAVE, "导出配置", False, self.navigationInterface)
        export_btn.clicked.connect(self.export_config)
        import_btn = NavigationPushButton(FluentIcon.FOLDER, "导入配置", False, self.navigationInterface)
        import_btn.clicked.connect(self.import_config)
        self.titleBar.raise_()  # 确保标题栏在顶层
        self.navigationInterface.addWidget(  # type: ignore
            routeKey="export",
            widget=export_btn,
            onClick=None,
            position=NavigationItemPosition.BOTTOM
        )
        self.navigationInterface.addWidget(  # type: ignore
            routeKey="import",
            widget=import_btn,
            onClick=None,
            position=NavigationItemPosition.BOTTOM
        )

    # ---------------- 导入/导出 -----------------
    def export_config(self):
        try:
            cfg = self.general.build_config()
        except ValidationError:
            return
        fn, _ = QFileDialog.getSaveFileName(self, "导出配置为 JSON", "config.json", "JSON (*.json)")
        if not fn:
            return
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(json.loads(cfg.model_dump_json()), f, ensure_ascii=False, indent=2)
        show_success(self, "已导出", os.path.basename(fn))

    def import_config(self):
        fn, _ = QFileDialog.getOpenFileName(self, "导入配置 JSON", "", "JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 回填到界面（允许缺省）
            self._fill_general(data)
            self._fill_advanced(data)
            show_success(self, "已导入", os.path.basename(fn))
        except Exception as e:
            show_error(self, "导入失败", str(e))

    def _fill_general(self, d: dict):
        if v := d.get("save_to"):
            self.general.save_to_combo.setCurrentText(v)
        if v := d.get("codec"):
            self.general.codec_combo.setCurrentText(v)
        hw = d.get("hwaccel")
        self.general.hwaccel_combo.setCurrentIndex(0 if hw in (None, "", "None") else max(1, self.general.hwaccel_combo.findText(str(hw))))
        if v := d.get("resolution"):
            self.general.resolution_edit.setText(v)
        if v := d.get("fps"):
            self.general.fps_spin.setValue(int(v))
        if v := d.get("video_ext"):
            if isinstance(v, list):
                self.general.video_ext_edit.setText(",".join(v))
            else:
                self.general.video_ext_edit.setText(str(v))
        if v := d.get("compress_dir_name"):
            self.general.compress_dir_edit.setText(v)
        if v := d.get("disable_hwaccel_when_fail") is not None:
            self.general.disable_hw_switch.setChecked(bool(v))

    def _fill_advanced(self, d: dict):
        crf = d.get("crf")
        bitrate = d.get("bitrate")
        if crf is not None and bitrate is None:
            self.advanced.mode_combo.setCurrentText("CRF 模式")
            self.advanced.crf_spin.setValue(int(crf))
            self.advanced.bitrate_edit.clear()
        else:
            self.advanced.mode_combo.setCurrentText("比特率模式")
            if bitrate is not None:
                self.advanced.bitrate_edit.setText(str(bitrate))
        if v := d.get("extra"):
            self.advanced.extra_edit.setPlainText("\n".join(v if isinstance(v, list) else [str(v)]))
        if v := d.get("manual"):
            self.advanced.manual_switch.setChecked(True)
            self.advanced.manual_edit.setEnabled(True)
            self.advanced.manual_edit.setPlainText("\n".join(v if isinstance(v, list) else [str(v)]))
        if v := d.get("ffmpeg"):
            self.advanced.ffmpeg_edit.setText(str(v))
        if v := d.get("ffprobe"):
            self.advanced.ffprobe_edit.setText(str(v))
        if v := d.get("test_video_resolution"):
            self.advanced.test_res_edit.setText(str(v))
        if v := d.get("test_video_fps"):
            self.advanced.test_fps_spin.setValue(int(v))
        if v := d.get("test_video_input"):
            self.advanced.test_in_edit.setText(str(v))
        if v := d.get("test_video_output"):
            self.advanced.test_out_edit.setText(str(v))


# --------------------------- 入口 --------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
