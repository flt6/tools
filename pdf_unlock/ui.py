from __future__ import annotations
from pathlib import Path
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from tkinterdnd2 import TkinterDnD, DND_FILES  # type: ignore
DND_AVAILABLE = True

from main import copy_pdf_pages  # type: ignore

APP_TITLE = "PDF 解锁（拖入即可）"
SUFFIX = "_decrypt"


def parse_dropped_paths(tcl_list: str, tk_root: tk.Misc) -> list[Path]:
    """将 DND 的 raw 字符串解析为 Path 列表（兼容空格/花括号）。"""
    return [Path(p) for p in tk_root.tk.splitlist(tcl_list)]


def gather_pdfs(paths: list[Path]) -> list[Path]:
    """根据传入路径自动识别：单文件 / 多文件 / 目录（递归），提取所有 PDF。"""
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend([f for f in p.rglob("*.pdf") if f.is_file()])
        elif p.is_file() and p.suffix.lower() == ".pdf":
            out.append(p)
    # 去重并按路径排序
    uniq = sorted({f.resolve() for f in out})
    return list(uniq)


def output_path_for(in_path: Path) -> Path:
    return in_path.with_name(f"{in_path.stem}{SUFFIX}.pdf")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("720x360")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # ---- 单一可点击/可拖拽区域 ----
        self.drop = ctk.CTkFrame(self.root, height=240, corner_radius=12)
        self.drop.pack(fill="both", expand=True, padx=20, pady=20)

        self.label = ctk.CTkLabel(
            self.drop,
            text=(
                "将 PDF 文件或文件夹拖入此区域即可开始解锁\n"
                "输出在原文件同目录，文件名加上 _decrypt 后缀"
                + ("（拖拽可用）")
            ),
            font=("微软雅黑", 16),
            justify="center",
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        # 点击同样可选择（依然只有这一个控件）
        self.drop.bind("<Button-1>", self._on_click_select)
        self.label.bind("<Button-1>", self._on_click_select)

        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES)  # type: ignore
            self.drop.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore

    # ---- 事件 ----
    def _on_click_select(self, _evt=None):
        # 仅一个简单文件选择器；若想选目录，可直接把目录拖进来
        files = filedialog.askopenfilenames(
            title="选择 PDF 文件（可多选）",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if files:
            self._start_process([Path(f) for f in files])

    def _on_drop(self, event):
        try:
            paths = parse_dropped_paths(event.data, self.root)
        except Exception:
            return
        self._start_process(paths)

    # ---- 核心处理 ----
    def _start_process(self, raw_paths: list[Path]):
        if copy_pdf_pages is None:
            messagebox.showerror(
                "错误",
                "未能从 main.py 导入 copy_pdf_pages(input_path: Path, output_path: Path) -> bool",
            )
            return

        pdfs = gather_pdfs(raw_paths)
        if not pdfs:
            messagebox.showwarning("提示", "未找到任何 PDF 文件。")
            return

        # 后台线程，避免 UI 卡死
        self.label.configure(text=f"发现 {len(pdfs)} 个 PDF，开始处理…")
        t = threading.Thread(target=self._worker, args=(pdfs,), daemon=True)
        t.start()

    def _worker(self, pdfs: list[Path]):
        ok, fail = 0, 0
        errors: list[str] = []
        for f in pdfs:
            try:
                out_path = output_path_for(f)
                # 简化：若已存在，直接覆盖
                out_path.parent.mkdir(parents=True, exist_ok=True)
                success = bool(copy_pdf_pages(f, out_path))  # type: ignore
                if success:
                    ok += 1
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                errors.append(f"{f}: {e}{traceback.format_exc()}")

        summary = f"完成：成功 {ok}，失败 {fail}。输出文件位于各自原目录。"
        self._set_status(summary)
        if errors:
            # 仅在有错误时弹出详情
            messagebox.showerror("部分失败", summary + "\n" + "\n".join(errors[:3]))
        else:
            messagebox.showinfo("完成", summary)

    def _set_status(self, text: str):
        self.label.configure(text=text)


def main():
    root: tk.Misc
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()  # type: ignore
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
