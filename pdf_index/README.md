# Streamlit PDF 目录查看器

一个最小可运行的 Streamlit 应用：
- 读取 `doc.pdf`（放在当前目录），或通过页面上传 PDF。
- 使用 PyMuPDF 提取 PDF 目录（Table of Contents）。
- 在下拉框选择目录项后，显示该目录项对应的页面范围（到下一个目录项前一页）。
- 使用 `st.pdf` 组件内嵌查看选定页面范围的临时 PDF。

## 快速开始（Windows / cmd）

1) 建议创建虚拟环境（可选）
```cmd
python -m venv .venv
.venv\Scripts\activate
```

2) 安装依赖
```cmd
pip install -r requirements.txt
```

3) 将你的 PDF 放到本目录并命名为 `doc.pdf`（或在页面中上传）。

4) 运行应用
```cmd
streamlit run app.py
```

## 用法说明
- 左侧边栏可上传 PDF；若本地存在 `doc.pdf`，也会自动被加载。
- 目录下拉框显示形如 `title (page)`。
- 若 PDF 无目录，本应用会提示；可选择“全部页面”查看。

## 已知限制
- 目录页码通常为 PDF 内部页码（从 1 开始），个别 PDF 的 TOC 可能与实际页面偏移不一致。
- 页面范围切片依赖 TOC 顺序，若 TOC 不规范可能导致范围不准。

## 说明

使用streamlit_pdf_viewer而不是官方的streamlit_pdf，是因为在手机上，streamlit_pdf无法显示。