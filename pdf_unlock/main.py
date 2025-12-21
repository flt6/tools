import PyPDF2  # PyMuPDF
from PyPDF2.generic import IndirectObject
import sys
from pathlib import Path
from typing import Optional
from itertools import repeat

def copy_pdf_pages(input_path: Path, output_path: Path) -> bool:
    """
    移除PDF文件的所有限制
    
    Args:
        input_path: 输入PDF文件路径
        output_path: 输出PDF文件路径
        password: PDF密码（如果有）
        
    Returns:
        是否成功移除限制
    """
    try:
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)

            try:
                que = list(zip(repeat(None),reader.outline))
                last:Optional[IndirectObject] = None
                for par, it in que:
                    if isinstance(it, list):
                        que.extend(zip(repeat(last),it))
                        continue
                    
                    title = getattr(it, 'title', None)
                    if title is None:
                        try:
                            title = str(it)
                        except Exception:
                            print(f"警告：无法获取书签标题，跳过该书签.")
                            continue

                    page_num = reader.get_destination_page_number(it)
                    if page_num is None:
                        continue
                    
                    last = writer.add_outline_item(title, page_num, parent=par)
            except Exception as e:
                print(f"警告：{input_path.name}书签处理失败.")
            
            # 写入新文件（不设置任何加密或限制）
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
            
    except Exception as e:
        print(f"移除PDF限制时发生错误: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法：python main.py <输入PDF文件或目录>")
        sys.exit(1)
    
    if len(sys.argv) > 2:
        files = list(map(Path, sys.argv[1:]))
    else:
        input_path = Path(sys.argv[1])
        if input_path.is_dir():
            files = list(input_path.rglob("*.pdf"))
        else:
            print("正在处理",input_path.name)
            output_file = input_path.with_name(f"{input_path.stem}_decrypt.pdf")
            suc = copy_pdf_pages(input_path, output_file)
            print("处理完成" if suc else "处理失败")
            return
    
    total = len(files)
    # 执行复制操作
    for i, pdf_file in enumerate(files, start=1):
        rate= round(i/total *100)
        print(f"进度: ", "-"* (rate//5)," "*(20-rate//5), f"   {rate}%",sep="",end="\r")
        if not pdf_file.is_file():
            print(f"跳过非PDF文件：{pdf_file}")
            continue
        output_file = pdf_file.with_name(f"{pdf_file.stem}_decrypt.pdf")
        suc = copy_pdf_pages(pdf_file, output_file)

        if not suc:
            print(f"{pdf_file.name} 处理失败")

if __name__ == "__main__":
    main()