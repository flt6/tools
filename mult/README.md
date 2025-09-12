# mult

批量视频处理工具。

## 功能

使用auto-editor和FFmpeg对多个MP4/FLV视频文件进行批量处理，自动去除静音片段并转码视频，支持并行处理提高效率。

## 使用方法

1. 将要处理的视频文件放在程序目录中
2. 运行 `python main.py`（CPU处理）或 `python main_up.py`（GPU加速）
3. 程序将自动处理所有视频文件

## 支持格式

- MP4
- FLV

## 特性

- 批量视频处理
- 自动静音片段移除
- 并行处理支持
- GPU硬件加速支持（main_up.py）
- 进程池管理

## 依赖要求

- FFmpeg
- auto-editor
- 足够的磁盘空间用于输出文件