from dataclasses import dataclass
from typing import Any, List, Optional, Tuple
from pathlib import Path

import fitz  # PyMuPDF
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer


@dataclass
class TocItem:
    level: int
    title: str
    page_from: int  # 1-based
    page_to: Optional[int]  # 1-based inclusive; None means until end


def read_toc(doc: fitz.Document) -> List[Tuple[int, str, int]]:
    # Returns list of (level, title, page) where page is 1-based per PyMuPDF
    toc: List[Tuple[int, str, int]] = []
    try:
        get_toc: Any = getattr(doc, "get_toc", None)
        if callable(get_toc):
            toc = get_toc(simple=True)  # type: ignore[no-any-return]
    except Exception:
        toc = []
    return [(lvl, title, max(1, pg)) for (lvl, title, pg) in toc]


def normalize_ranges(toc: List[Tuple[int, str, int]], page_count: int) -> List[TocItem]:
    if not toc:
        return []
    items: List[TocItem] = []
    for i, (lvl, title, page) in enumerate(toc):
        start = min(max(1, page), page_count)
        if i + 1 < len(toc):
            next_page = toc[i + 1][2]
            end = max(1, min(page_count, next_page - 1))
            if end < start:
                end = start
        else:
            end = page_count
        items.append(TocItem(level=lvl, title=title, page_from=start, page_to=end))
    return items


def _hash_doc(doc:fitz.Document):
    "This is a fake hash, ENSURE GLOBAL DOCUMENT SAME"
    return "12"

@st.cache_resource(hash_funcs={fitz.Document:_hash_doc})
def slice_pdf_pages(src_doc: fitz.Document, page_from: int, page_to: int) -> bytes:
    # Create a new PDF with selected 1-based inclusive page range
    new_pdf = fitz.open()
    try:
        start_i = max(1, page_from) - 1
        end_i = max(start_i, page_to - 1)
        for p in range(start_i, min(end_i, src_doc.page_count - 1) + 1):
            new_pdf.insert_pdf(src_doc, from_page=p, to_page=p)
        out = new_pdf.tobytes()
        return out
    finally:
        new_pdf.close()
        src_doc.close()


def format_label(item: TocItem) -> str:
    return f"{item.title} ({item.page_from:03d} - {item.page_to:03d})"

@st.cache_resource
def read_pdf():
    pdf_path = Path("doc.pdf")
    if not pdf_path.exists():
        st.error("找不到doc.pdf")
        st.stop()
    
    doc = fitz.open(pdf_path, filetype="pdf")
    def _close_doc():
        "Never close doc due to cache in global streamlit app."
        pass
    doc.close = _close_doc
    page_count = doc.page_count

    # 读取目录
    raw_toc = read_toc(doc)
    items = normalize_ranges(raw_toc, page_count)
        
    return doc,page_count,items


def main():
    st.set_page_config(page_title="PDF 目录查看器", layout="wide")
    st.title("PDF 目录查看器")

    doc,page_count,items = read_pdf()

    st.subheader("目录")
    labels = ["请选择"] + [format_label(it) for it in items]
    selection = st.selectbox("选择章节", labels, index=0)
    if selection == "请选择":
        st.stop()
    idx = labels.index(selection)
    chosen = items[idx]
    selected_range = (chosen.page_from, chosen.page_to or page_count)

    rng_from, rng_to = selected_range
    
    st.subheader("预览")
    try:
        sliced_bytes = slice_pdf_pages(doc, rng_from, rng_to)
        st.download_button("下载",sliced_bytes,file_name=f"{chosen.title}.pdf")
        pdf_viewer(sliced_bytes,rendering=st.session_state.get("render","unwrap"))
        # st.pdf(io.BytesIO(sliced_bytes), height=height, key="pdf_preview")
    except Exception as e:
        st.error(f"渲染失败：{e}")
        
    st.selectbox("使用其他渲染方式",["unwrap","legacy_embed","legacy_iframe"],key="render")


if __name__ == "__main__":
    main()
