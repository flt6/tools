import PyPDF2  # PyMuPDF
import sys
from pathlib import Path

def copy_pdf_pages(input_path: str, output_path: str) -> bool:
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
            
            # 写入新文件（不设置任何加密或限制）
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
            
    except Exception as e:
        print(f"移除PDF限制时发生错误: {e}")
        return False

# def copy_pdf_pages(input_file, output_file):
#     """
#     读取PDF文件并逐页复制到新的PDF文件
    
#     Args:
#         input_file (str): 输入PDF文件路径
#         output_file (str): 输出PDF文件路径
#     """
#     try:
#         # 检查输入文件是否存在
#         if not os.path.exists(input_file):
#             print(f"错误：输入文件 '{input_file}' 不存在")
#             return False
        
#         # 打开输入PDF文件
#         pdf_document = fitz.open(input_file)
        
#         # 创建新的PDF文档
#         new_pdf = fitz.open()
#         new_pdf.insert_pdf(pdf_document)
        
#         # 保存输出文件
#         new_pdf.save(output_file)
        
#         # 关闭文档
#         pdf_document.close()
#         new_pdf.close()
        
#         return True
            
#     except FileNotFoundError:
#         print(f"错误：找不到文件 '{input_file}'")
#         return False
#     except PermissionError:
#         print(f"错误：权限不足，无法访问文件")
#         return False
#     except Exception as pdf_error:
#         error_msg = str(pdf_error).lower()
#         if "damaged" in error_msg or "corrupt" in error_msg:
#             print(f"错误：PDF文件 '{input_file}' 已损坏")
#         else:
#             print(f"发生错误：{str(pdf_error)}")
#         return False

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
            files = list(input_path.glob("**/*.pdf"))
        else:
            print("正在处理",input_path.name)
            output_file = input_path.with_name(f"{input_path.stem}_decrypt.pdf")
            success = copy_pdf_pages(input_path, output_file)
            print("处理完成" if success else "处理失败")
            return
    
    total = len(files)
    # 执行复制操作
    for i, pdf_file in enumerate(files, start=1):
        rate= round(i/total *100)
        print(f"进度: ", "-"* (rate//5)," "*(20-rate//5), f"   {rate}%",sep="",end="\r")
        import time
        # time.sleep(1)  # 模拟处理时间
        if not pdf_file.is_file():
            print(f"跳过非PDF文件：{pdf_file}")
            continue
        output_file = pdf_file.with_name(f"{pdf_file.stem}_decrypt.pdf")
        success = copy_pdf_pages(pdf_file, output_file)

        if not success:
            print(f"{pdf_file.name} 处理失败")

if __name__ == "__main__":
    main()