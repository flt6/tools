# 个人使用小工具集

## [修改连接数](changeConnectionLimit)

win10修改wifi热点最大连接终端数

Usage：`main.bat`

## [学*网预览下载](zxxk_dl)

下载学*网资源，通过预览的形式，下载的文件以html形式保存。可以使用adobe Acrobat的打印转为pdf，文字版文件以svg下载，图片版原图。

1. 研究过程：[process.md](zxxk_dl/process.md)

2. usage: `python main.py`
3. requirements: python, requests

## adb快速传手机文件

源文件丢了，TODO

2024.7.14：放弃，已有项目[双轨快传](https://github.com/weixiansen574/HybridFileXfer)实现

## [并行auto-editor](mult)

并行运行auto-editor, 递归转码所有视频。（PS：网课时用的）

### files

#### main.py

主程序

### main_up.py

使用hevc（CUDA）硬解码

### usage

`python main.py`

## 菁*网题目下载

**ATTENTION：目前制作时的账号疑似被封禁，请谨慎使用**

如需打印，请使用浏览器打印或转pdf

### Usage

菁优网任意界面，F12抓Cookie
运行main.py，输入复制的内容，根据提示输入网址即可。

### requements

python, requests,bs4

## [听力文件拆分](English_Listening_cut)

基于学英语报的听力做听力文件拆解，拆分到每段对话

### Usage

`python main.py`

## seat_map

文档TODO

## 简单运动报警(move_warn)

对ip摄像头画面进行简单运动捕捉，核心代码来自网络。效果：运动达到一定范围，发出声音警告后自动关闭程序。

### usage

`python main.py`

### requirements

python, opencv

## 检测视频是否破损（video_test）



## 转移libcef.dll（move_CEF）

通过Everything API遍历所有libcef.dll，核验md5后转移至指定文件夹并创建软连接。

## [图片整理(tidy_img)](tidy_img)

按照手机（华为）照片视频命名规范（例如`IMG_20170218_164951.jpg`，`VID_20220116_154728.mp4`）将其按年份分类，递归遍历所有文件。如果重复，文件相同<sup>[1]</sup>由用户判断是否删除相同文件。如果文件冲突<sup>[2]</sup>，放入conflict文件夹，并在文件名后加sha256前5位。

[1]: 先判断文件大小，相同比较sha256值，如果均相同认为是同文件
[2]: 上述标准任一不满足
