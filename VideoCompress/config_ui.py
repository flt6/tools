import sys
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QLabel, QComboBox, QSpinBox, QLineEdit, QPushButton,
    QCheckBox, QSlider, QGroupBox, QFileDialog, QMessageBox,
    QFrame, QSizePolicy, QToolTip
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette


@dataclass
class VideoConfig:
    """视频压缩配置数据类"""
    save_to: str = "multi"
    crf: int = 18
    codec: str = "h264"
    ffmpeg: str = "ffmpeg"
    video_ext: List[str] = [".mp4", ".mkv"]
    extra: List[str] = []
    manual: Optional[List[str]] = None
    bitrate: Optional[str] = None
    
    def __post_init__(self):
        if self.video_ext is None:
            self.video_ext = [".mp4", ".mkv"]
        if self.extra is None:
            self.extra = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoConfig':
        """从字典创建配置对象"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_crf(value: int) -> bool:
        return 0 <= value <= 51
    
    @staticmethod
    def validate_bitrate(value: str) -> bool:
        if not value:
            return True
        return value.endswith(('M', 'k', 'K')) and value[:-1].replace('.', '').isdigit()
    
    @staticmethod
    def validate_ffmpeg_path(path: str) -> bool:
        if path == "ffmpeg":  # 系统PATH中的ffmpeg
            return True
        return os.path.isfile(path) and path.lower().endswith(('.exe', ''))


class QCollapsibleGroupBox(QGroupBox):
    """可折叠的GroupBox"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self._on_toggled)
        
        # 设置特殊样式
        self.setStyleSheet("""
            QCollapsibleGroupBox {
                font-weight: bold;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
                color: #495057;
            }
            QCollapsibleGroupBox:hover {
                border-color: #ffc107;
                background-color: #fffdf5;
            }
            QCollapsibleGroupBox:checked {
                border-color: #28a745;
                background-color: #f8fff9;
            }
            QCollapsibleGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #495057;
                background-color: transparent;
            }
            QCollapsibleGroupBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #ced4da;
                background-color: white;
            }
            QCollapsibleGroupBox::indicator:hover {
                border-color: #ffc107;
                background-color: #fffdf5;
            }
            QCollapsibleGroupBox::indicator:checked {
                background-color: #28a745;
                border-color: #28a745;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
        """)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.content_widget)
        
        self.content_widget.hide()
    
    def _on_toggled(self, checked: bool):
        self.content_widget.setVisible(checked)
        window:ConfigUI = self.parent().parent()
        assert(isinstance(window,ConfigUI))
        # 添加展开/收缩的动画效果提示
        if checked:
            window.setMinimumSize(520,900)
            self.setToolTip("点击收起高级设置")
        else:
            size = window.size()
            window.setMinimumSize(520,650)
            window.resize(size.width(),size.height()-200)
            self.setToolTip("点击展开高级设置")
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class ConfigUI(QMainWindow):
    """现代化的配置界面"""
    
    # 常量定义
    SAVE_METHODS = {
        "single": "保存到统一文件夹",
        "multi": "每个视频旁建立文件夹"
    }
    
    GPU_BRANDS = {
        "none": "不使用GPU加速",
        "nvidia": "NVIDIA显卡",
        "amd": "AMD显卡", 
        "intel": "Intel核显"
    }
    
    CODEC_TYPES = {
        "h264": "H.264 (兼容性好)",
        "hevc": "H.265 (体积更小)"
    }
    
    PRESET_OPTIONS = {
        "none": ["", "ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
        "nvidia": ["", "default", "slow", "medium", "fast", "hp", "hq"],
        "amd": ["", "speed", "balanced", "quality"],
        "intel": ["", "veryfast", "faster", "fast", "medium", "slow"]
    }
    
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self._setup_ui()
        self._connect_signals()
        self._load_values()
        
    def _load_config(self) -> VideoConfig:
        """加载配置文件"""
        config_path = self._get_config_path()
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return VideoConfig.from_dict(data)
        except Exception as e:
            QMessageBox.warning(self, "配置加载", f"配置文件加载失败，使用默认设置\n{e}")
        
        return VideoConfig()
    
    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        if os.environ.get("INSTALL", "0") == "1":
            return Path(os.getenv("APPDATA", "C:/")) / "VideoCompress" / "config.json"
        else:
            return Path(sys.path[0]) / "config.json"
    
    def _setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("🎬 视频压缩配置")
        self.setMinimumSize(520, 650)
        self.resize(520, 700)
        self._apply_modern_style()
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题
        title_label = QLabel("视频压缩工具配置")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #343a40;
                padding: 10px 0;
                border-bottom: 2px solid #e9ecef;
                margin-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 基础设置组
        basic_group = self._create_basic_group()
        main_layout.addWidget(basic_group)
        
        # 质量设置组
        quality_group = self._create_quality_group()
        main_layout.addWidget(quality_group)
        
        # 硬件加速组
        hardware_group = self._create_hardware_group()
        main_layout.addWidget(hardware_group)
        
        # 高级设置组（可折叠）
        advanced_group = self._create_advanced_group()
        main_layout.addWidget(advanced_group)
        
        # 按钮区域
        button_layout = self._create_buttons()
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
    
    def _apply_modern_style(self):
        """应用现代化样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
                color: #495057;
            }
            QGroupBox:hover {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            QGroupBox:focus {
                border-color: #007bff;
                background-color: #f0f4ff;
                outline: none;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #495057;
                background-color: transparent;
            }
            QGroupBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #ced4da;
                background-color: white;
            }
            QGroupBox::indicator:hover {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            QGroupBox::indicator:checked {
                background-color: #007bff;
                border-color: #007bff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
            QComboBox, QLineEdit, QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                font-size: 14px;
                color: #495057;
            }
            QComboBox:hover, QLineEdit:hover, QSpinBox:hover {
                border-color: #007bff;
            }
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus {
                border-color: #007bff;
                background-color: #f8f9ff;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDEuNUw2IDYuNUwxMSAxLjUiIHN0cm9rZT0iIzQ5NTA1NyIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
                width: 12px;
                height: 8px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #003f7f;
            }
            QSlider::groove:horizontal {
                border: 1px solid #ced4da;
                background: #f8f9fa;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007bff;
                border: 2px solid #0056b3;
                width: 20px;
                height: 20px;
                margin: -7px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #0056b3;
                border-color: #003f7f;
            }
            QSlider::sub-page:horizontal {
                background: #007bff;
                border-radius: 4px;
            }
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
                color: #495057;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #ced4da;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
            QCheckBox::indicator:checked {
                background-color: #007bff;
                border-color: #007bff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
            QLabel {
                color: #495057;
                font-size: 14px;
            }
            QToolTip {
                background-color: #212529;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
    
    def _create_basic_group(self) -> QGroupBox:
        """创建基础设置组"""
        group = QGroupBox("⚙️ 基础设置")
        layout = QGridLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # 输出方式
        output_label = QLabel("输出方式:")
        output_label.setToolTip("选择压缩后的视频文件保存方式")
        layout.addWidget(output_label, 0, 0)
        self.save_method_combo = QComboBox()
        self.save_method_combo.addItems(list(self.SAVE_METHODS.values()))
        self.save_method_combo.setToolTip("选择输出文件的保存位置")
        layout.addWidget(self.save_method_combo, 0, 1)
        
        # 编码器类型
        codec_label = QLabel("编码器:")
        codec_label.setToolTip("选择视频编码格式")
        layout.addWidget(codec_label, 1, 0)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(list(self.CODEC_TYPES.values()))
        self.codec_combo.setToolTip("H.264兼容性更好，H.265文件更小")
        layout.addWidget(self.codec_combo, 1, 1)
        
        return group
    
    def _create_quality_group(self) -> QGroupBox:
        """创建质量设置组"""
        group = QGroupBox("质量设置")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(12)
        
        # CRF/码率选择
        mode_layout = QHBoxLayout()
        self.crf_radio = QCheckBox("使用CRF (推荐)")
        self.bitrate_radio = QCheckBox("使用固定码率")
        self.crf_radio.setChecked(True)
        self.crf_radio.setToolTip("CRF模式可以保持恒定质量，推荐使用")
        self.bitrate_radio.setToolTip("固定码率模式可以控制文件大小")
        mode_layout.addWidget(self.crf_radio)
        mode_layout.addWidget(self.bitrate_radio)
        layout.addLayout(mode_layout)
        
        # CRF滑块
        crf_layout = QHBoxLayout()
        quality_label = QLabel("质量:")
        quality_label.setToolTip("数值越小质量越高，文件越大")
        crf_layout.addWidget(quality_label)
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(18)
        self.crf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.crf_slider.setTickInterval(10)
        self.crf_slider.setToolTip("拖动调整视频质量")
        crf_layout.addWidget(self.crf_slider)
        
        self.crf_label = QLabel("18 (高质量)")
        self.crf_label.setMinimumWidth(80)
        self.crf_label.setStyleSheet("font-weight: bold; color: #007bff;")
        crf_layout.addWidget(self.crf_label)
        layout.addLayout(crf_layout)
        
        # 码率输入
        bitrate_layout = QHBoxLayout()
        bitrate_label = QLabel("码率:")
        bitrate_label.setToolTip("指定视频的码率")
        bitrate_layout.addWidget(bitrate_label)
        self.bitrate_edit = QLineEdit()
        self.bitrate_edit.setPlaceholderText("例如: 2M, 500k")
        self.bitrate_edit.setEnabled(False)
        self.bitrate_edit.setToolTip("输入目标码率，如2M表示2Mbps")
        bitrate_layout.addWidget(self.bitrate_edit)
        layout.addLayout(bitrate_layout)
        
        return group
    
    def _create_hardware_group(self) -> QGroupBox:
        """创建硬件加速组"""
        group = QGroupBox("🚀 硬件加速")
        layout = QGridLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(12)
        
        # GPU品牌选择
        gpu_label = QLabel("GPU品牌:")
        gpu_label.setToolTip("选择您的显卡品牌以启用硬件加速")
        layout.addWidget(gpu_label, 0, 0)
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(list(self.GPU_BRANDS.values()))
        self.gpu_combo.setToolTip("硬件加速可以显著提升编码速度")
        layout.addWidget(self.gpu_combo, 0, 1)
        
        # 预设选择
        preset_label = QLabel("压缩预设:")
        preset_label.setToolTip("选择编码预设以平衡速度和质量")
        layout.addWidget(preset_label, 1, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("fast模式速度快但质量稍低，slow模式质量高但速度慢")
        layout.addWidget(self.preset_combo, 1, 1)
        
        return group
    
    def _create_advanced_group(self) -> QCollapsibleGroupBox:
        """创建高级设置组"""
        group = QCollapsibleGroupBox("高级设置")
        group.setToolTip("点击展开高级设置选项")
        
        # FFmpeg路径
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_label = QLabel("FFmpeg路径:")
        ffmpeg_label.setToolTip("指定FFmpeg程序的路径")
        ffmpeg_layout.addWidget(ffmpeg_label)
        self.ffmpeg_edit = QLineEdit()
        self.ffmpeg_edit.setPlaceholderText("ffmpeg")
        self.ffmpeg_edit.setToolTip("留空使用系统PATH中的ffmpeg")
        ffmpeg_layout.addWidget(self.ffmpeg_edit)
        
        self.ffmpeg_browse_btn = QPushButton("📂 浏览")
        self.ffmpeg_browse_btn.setMaximumWidth(80)
        self.ffmpeg_browse_btn.setToolTip("浏览选择FFmpeg可执行文件")
        ffmpeg_layout.addWidget(self.ffmpeg_browse_btn)
        group.addLayout(ffmpeg_layout)
        
        # 支持的视频格式
        ext_layout = QHBoxLayout()
        ext_label = QLabel("🎬 视频格式:")
        ext_label.setToolTip("指定支持的视频文件格式")
        ext_layout.addWidget(ext_label)
        self.ext_edit = QLineEdit()
        self.ext_edit.setPlaceholderText(".mp4,.mkv,.avi")
        self.ext_edit.setToolTip("用逗号分隔多个格式")
        ext_layout.addWidget(self.ext_edit)
        group.addLayout(ext_layout)
        
        # 自定义参数
        custom_layout = QVBoxLayout()
        custom_label = QLabel("自定义FFmpeg参数:")
        custom_label.setToolTip("高级用户可以添加自定义FFmpeg参数")
        custom_layout.addWidget(custom_label)
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("高级用户使用，例如: -threads 4")
        self.custom_edit.setToolTip("添加额外的FFmpeg命令行参数")
        custom_layout.addWidget(self.custom_edit)
        group.addLayout(custom_layout)
        
        # 实验性功能
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """创建按钮区域"""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addStretch()
        
        # 重置按钮
        reset_btn = QPushButton("🔄 重置")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
            QPushButton:pressed {
                background-color: #3d4142;
            }
        """)
        reset_btn.setToolTip("重置所有设置为默认值")
        reset_btn.clicked.connect(self._reset_config)
        layout.addWidget(reset_btn)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        save_btn.setToolTip("保存当前配置")
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)
        
        # 退出按钮
        exit_btn = QPushButton("❌ 退出")
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        exit_btn.setToolTip("退出配置程序")
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)
        
        return layout
    
    def _connect_signals(self):
        """连接信号和槽"""
        # CRF滑块更新标签
        self.crf_slider.valueChanged.connect(self._update_crf_label)
        
        # CRF/码率模式切换
        self.crf_radio.toggled.connect(self._toggle_quality_mode)
        self.bitrate_radio.toggled.connect(self._toggle_quality_mode)
        
        # GPU品牌变化时更新预设选项
        self.gpu_combo.currentTextChanged.connect(self._update_preset_options)
        
        # FFmpeg浏览按钮
        self.ffmpeg_browse_btn.clicked.connect(self._browse_ffmpeg)
        
        # 实时验证
        self.bitrate_edit.textChanged.connect(self._validate_bitrate)
    
    def _update_crf_label(self, value: int):
        """更新CRF标签显示"""
        if value <= 18:
            quality = "高质量"
        elif value <= 23:
            quality = "平衡"
        elif value <= 28:
            quality = "压缩优先"
        else:
            quality = "高压缩"
        
        self.crf_label.setText(f"{value} ({quality})")
    
    def _toggle_quality_mode(self):
        """切换质量模式"""
        if self.sender() == self.crf_radio:
            if self.crf_radio.isChecked():
                self.bitrate_radio.setChecked(False)
                self.crf_slider.setEnabled(True)
                self.bitrate_edit.setEnabled(False)
        else:  # bitrate_radio
            if self.bitrate_radio.isChecked():
                self.crf_radio.setChecked(False)
                self.crf_slider.setEnabled(False)
                self.bitrate_edit.setEnabled(True)
    
    def _update_preset_options(self, gpu_text: str):
        """根据GPU品牌更新预设选项"""
        gpu_key = None
        for key, value in self.GPU_BRANDS.items():
            if value == gpu_text:
                gpu_key = key
                break
        
        if gpu_key == "none":
            preset_key = "none"
        elif gpu_key == "nvidia":
            preset_key = "nvidia"
        elif gpu_key == "amd":
            preset_key = "amd"
        elif gpu_key == "intel":
            preset_key = "intel"
        else:
            preset_key = "none"
        
        self.preset_combo.clear()
        options = self.PRESET_OPTIONS.get(preset_key, [""])
        display_options = ["默认"] + [opt if opt else "无" for opt in options[1:]]
        self.preset_combo.addItems(display_options)
    
    def _browse_ffmpeg(self):
        """浏览FFmpeg文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择FFmpeg可执行文件", "", 
            "可执行文件 (*.exe);;所有文件 (*)"
        )
        if file_path:
            self.ffmpeg_edit.setText(file_path)
    
    def _validate_bitrate(self, text: str):
        """验证码率输入"""
        if text and not ConfigValidator.validate_bitrate(text):
            self.bitrate_edit.setStyleSheet("border: 2px solid #dc3545;")
            QToolTip.showText(self.bitrate_edit.mapToGlobal(self.bitrate_edit.rect().center()),
                            "码率格式错误，应为数字+M/k，例如：2M、500k")
        else:
            self.bitrate_edit.setStyleSheet("")
    
    def _load_values(self):
        """加载配置值到界面"""
        # 基础设置
        save_method_text = self.SAVE_METHODS.get(self.config.save_to, list(self.SAVE_METHODS.values())[0])
        self.save_method_combo.setCurrentText(save_method_text)
        
        # 编码器
        codec_base = "h264"
        if self.config.codec.startswith("hevc"):
            codec_base = "hevc"
        self.codec_combo.setCurrentText(self.CODEC_TYPES[codec_base])
        
        # 质量设置
        if hasattr(self.config, 'bitrate') and self.config.bitrate:
            self.bitrate_radio.setChecked(True)
            self.bitrate_edit.setText(self.config.bitrate)
            self.crf_slider.setEnabled(False)
            self.bitrate_edit.setEnabled(True)
        else:
            print(self.config)
            self.crf_radio.setChecked(True)
            self.crf_slider.setValue(self.config.crf)
            self.bitrate_edit.setEnabled(False)
        
        # 硬件加速
        gpu_brand = "none"
        if "_nvenc" in self.config.codec:
            gpu_brand = "nvidia"
        elif "_amf" in self.config.codec:
            gpu_brand = "amd"
        elif "_qsv" in self.config.codec:
            gpu_brand = "intel"
        
        self.gpu_combo.setCurrentText(self.GPU_BRANDS[gpu_brand])
        self._update_preset_options(self.GPU_BRANDS[gpu_brand])
        
        # 预设
        preset_value = ""
        if "-preset" in self.config.extra:
            idx = self.config.extra.index("-preset")
            if idx + 1 < len(self.config.extra):
                preset_value = self.config.extra[idx + 1]
        
        if preset_value:
            for i in range(self.preset_combo.count()):
                if self.preset_combo.itemText(i) == preset_value:
                    self.preset_combo.setCurrentIndex(i)
                    break
        
        # 高级设置
        self.ffmpeg_edit.setText(self.config.ffmpeg)
        self.ext_edit.setText(",".join(self.config.video_ext))
        
        if self.config.manual:
            self.custom_edit.setText(" ".join(self.config.manual))
        
    
    def _save_config(self):
        """保存配置"""
        try:
            # 验证输入
            if self.bitrate_radio.isChecked():
                bitrate = self.bitrate_edit.text().strip()
                if bitrate and not ConfigValidator.validate_bitrate(bitrate):
                    QMessageBox.warning(self, "输入错误", "码率格式不正确！")
                    return
            
            # 构建配置
            config = VideoConfig()
            
            # 基础设置
            for key, value in self.SAVE_METHODS.items():
                if value == self.save_method_combo.currentText():
                    config.save_to = key
                    break
            
            # 编码器
            codec_base = "h264"
            for key, value in self.CODEC_TYPES.items():
                if value == self.codec_combo.currentText():
                    codec_base = key
                    break
            
            # GPU加速
            gpu_suffix = ""
            gpu_text = self.gpu_combo.currentText()
            if gpu_text == self.GPU_BRANDS["nvidia"]:
                gpu_suffix = "_nvenc"
            elif gpu_text == self.GPU_BRANDS["amd"]:
                gpu_suffix = "_amf"
            elif gpu_text == self.GPU_BRANDS["intel"]:
                gpu_suffix = "_qsv"
            
            config.codec = codec_base + gpu_suffix
            
            # 质量设置
            if self.crf_radio.isChecked():
                config.crf = self.crf_slider.value()
                config.bitrate = None
            else:
                config.bitrate = self.bitrate_edit.text().strip()
            
            # 其他设置
            config.ffmpeg = self.ffmpeg_edit.text().strip() or "ffmpeg"
            
            ext_text = self.ext_edit.text().strip()
            if ext_text:
                config.video_ext = [ext.strip() for ext in ext_text.split(",") if ext.strip()]
            
            config.extra = []
            
            # 预设
            preset_text = self.preset_combo.currentText()
            if preset_text and preset_text != "默认" and preset_text != "无":
                config.extra.extend(["-preset", preset_text])
            
            # 自定义参数
            custom_text = self.custom_edit.text().strip()
            if custom_text:
                config.manual = custom_text.split()
            
            
            # 保存文件
            config_path = self._get_config_path()
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=4)
            
            QMessageBox.information(self, "保存成功", "配置已保存成功！")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错：\n{e}")
    
    def _reset_config(self):
        """重置为默认配置"""
        reply = QMessageBox.question(self, "确认重置", "确定要重置为默认配置吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.config = VideoConfig()
            self._load_values()


def main():
    """主函数"""
    if len(sys.argv)>1:
        import main
        sys.exit(main.main())
    
    app = QApplication()
    app.setStyle("Fusion")  # 使用现代风格
    
    # 设置应用信息
    app.setApplicationName("视频压缩配置")
    app.setApplicationVersion("1.3")
    app.setOrganizationName("VideoCompress")
    
    window = ConfigUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()