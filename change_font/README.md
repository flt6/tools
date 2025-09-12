# change_font

An OCR-powered tool that detects text in images and replaces it with custom fonts.

说明：用于将已有文档所有手写文字转变为自定义字体，尽量保持文字格式位置不变。

注意：**只将手写替换，保持印刷体不变。**

使用好未来（https://ai.100tal.com/）的API，可能需要付费。

## Description

This tool uses optical character recognition (OCR) to identify text within images and replaces the detected text with your choice of custom fonts, maintaining the original layout and positioning.

## Usage

1. Configure your API credentials in the script
2. Place your source images in the designated folder
3. Run `python main.py`
4. The tool will process images and generate new versions with replaced fonts

## Requirements

- Python libraries: opencv, numpy, matplotlib, Pillow
- Valid API credentials for the OCR service
- Source images to process

## Setup

Before running, make sure to:
- Install required Python packages
- Configure your API credentials in the configuration section
- Prepare your input images in the correct format