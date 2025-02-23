import subprocess
from pathlib import Path
import sys
import logging
from datetime import datetime
from time import time
from rich.logging import RichHandler
from rich.progress import Progress
from pickle import dumps,loads
import numpy as np
import atexit

root = None
TRAIN = False
ESTI_FILE = Path("esti.out")
esti=None # :tuple[list[int],list[float]]

def train_init():
    global esti_data,TRAIN,data_file
    data_file = Path("estiminate_data.dat")
    if data_file.exists():
        esti_data=loads(data_file.read_bytes())
        if not isinstance(esti_data,tuple):
            esti_data=([],[])
    else:
        esti_data=([],[])
    TRAIN=True
    atexit.register(save_esti)
    # print(esti_data)


# 配置logging
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"video_compress_{datetime.now().strftime('%Y%m%d')}.log"
    stream = RichHandler(rich_tracebacks=True,tracebacks_show_locals=True)
    stream.setLevel(logging.DEBUG)
    stream.setFormatter(logging.Formatter("%(message)s"))
    
    file = logging.FileHandler(log_file, encoding='utf-8')
    file.setLevel(logging.INFO)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname) 7s - %(message)s',
        handlers=[
            file,
            stream
        ]
    )

def save_esti():
    func = np.polyfit(esti_data[0],esti_data[1],2)
    func.tofile(ESTI_FILE)

def fmt_time(t:int) -> str:
    if t>3600:
        return f"{t//3600}h {t//60}min {t%60}s"
    elif t>60:
        return f"{t//60}min {t%60}s"
    else:
        return f"{round(t)}s"

def func(sz:int,src=False):
    if TRAIN:
        try:
            data_file.write_bytes(dumps(esti_data))
        except KeyboardInterrupt as e:raise e
        except Exception as e:
            logging.warning("无法保存数据",exc_info=e)
    try:
        if TRAIN:
            if len(esti_data[0])==0:
                return -1 if src else "NaN"
            func = np.polyfit(esti_data[0],esti_data[1],2)
            t = func[0]*sz**2+func[1]*sz+func[2]
        elif esti is not None:
            t = esti[0]*sz**2+esti[1]*sz+esti[2]
            # print(t,sz)
        else:
            logging.warning(f"Unexpected condition at func->TRAIN")
            return -1 if src else "NaN"
        t = round(t)
        if src:
            return t
        return fmt_time(t)
    except KeyboardInterrupt as e:raise e
    except Exception as e:
        logging.warning("无法计算预计时间",exc_info=e)
        return -1 if src else "NaN"
    
def process_video(video_path: Path):
    global esti_data
    use=None
    sz=video_path.stat().st_size//(1024*1024)
    if esti is not None or TRAIN:
        use = func(sz,True)
        logging.debug(f"开始处理文件: {video_path.relative_to(root)}，大小{sz}M，预计{fmt_time(use)}")
    else:
        logging.debug(f"开始处理文件: {video_path.relative_to(root)}，大小{sz}M")
        
    
    bgn=time()
    # 在视频文件所在目录下创建 compress 子目录（如果不存在）
    compress_dir = video_path.parent / "compress"
    compress_dir.mkdir(exist_ok=True)
    
    # 输出文件路径：与原文件同名，保存在 compress 目录下
    output_file = compress_dir / (video_path.stem + video_path.suffix)
    if output_file.is_file():
        logging.warning(f"文件{output_file}存在，跳过")
        return use
    
    # 4x
    # command = [
    #     "ffmpeg.exe",  # 可以修改为 ffmpeg 的完整路径，例如：C:/ffmpeg/bin/ffmpeg.exe
    #     "-hide_banner",  # 隐藏 ffmpeg 的横幅信息
    #     "-i", str(video_path.absolute()),
    #     "-filter:v", "setpts=0.25*PTS",  # 设置视频高度为 1080，宽度按比例自动计算
    #     "-filter:a", "atempo=4.0",
    #     "-c:v", "h264_qsv",  # 使用 Intel Quick Sync Video 编码
    #     "-global_quality", "28",  # 设置全局质量（数值越低质量越高）
    #     "-r","30",
    #     "-preset", "fast",  # 设置压缩速度为慢（压缩效果较好）
    #     "-y",
    #     str(output_file.absolute())
    # ]
    
    # 1x
    command = [
        "ffmpeg.exe",  
        "-hide_banner",  # 隐藏 ffmpeg 的横幅信息
        "-i", str(video_path.absolute()),
        "-vf", "scale=-1:1080",  # 设置视频高度为 1080，宽度按比例自动计算
        "-c:v", "h264_qsv",  # 使用 Intel Quick Sync Video 编码
        "-global_quality", "28",  # 设置全局质量（数值越低质量越高）
        "-c:a", "copy",  # 音频不做处理，直接拷贝
        "-r","30",
        "-preset", "slow",  # 设置压缩速度为慢（压缩效果较好）
        "-y",
        str(output_file)
    ]
    
    try:
        # 调用 ffmpeg，并捕获标准输出和错误信息
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding="utf-8", 
            text=True
        )
        
        # 检查 ffmpeg 的错误输出
        if result.stderr:
            # 记录所有警告和错误信息
            for line in result.stderr.splitlines():
                if 'warning' in line.lower():
                    logging.warning(f"[FFmpeg]({video_path}): {line}")
                elif 'error' in line.lower():
                    logging.error(f"[FFmpeg]({video_path}): {line}")
        
        # 检查 ffmpeg 执行的返回码
        if result.returncode != 0:
            logging.error(f"处理文件 {video_path} 失败，返回码: {result.returncode}，cmd={' '.join(command)}")
            logging.error(result.stdout)
            logging.error(result.stderr)
        else:
            logging.debug(f"文件处理成功: {video_path} -> {output_file}")
            
            end=time()
            if TRAIN:
                esti_data[0].append(sz)
                esti_data[1].append(end-bgn)
                
            
    except Exception as e:
        logging.error(f"执行 ffmpeg 命令时发生异常, 文件：{video_path}，cmd={' '.join(command)}",exc_info=e)
    return use

def traverse_directory(root_dir: Path):
    video_extensions = {".mp4", ".mkv"}
    sm=None
    if esti is not None:
        logging.info(f"正在估算时间（当存在大量小文件时，估算值将会很离谱）")
        sm = 0
        for file in root_dir.rglob("*"):
            if file.parent.name == "compress":continue
            if file.is_file() and file.suffix.lower() in video_extensions:
                sz=file.stat().st_size//(1024*1024)
                tmp = func(sz,True)
                if not isinstance(tmp,int):
                    logging.error("无法预估时间，因为预估函数返回非整数")
                elif tmp == -1:
                    logging.error("无法预估时间，因为预估函数返回了异常")
                sm += tmp
        logging.info(f"预估用时：{fmt_time(sm)}")
        
        
    logging.debug(f"开始遍历目录: {root_dir}")
    # 定义需要处理的视频后缀（忽略大小写）
    
    with Progress() as prog:
        task = prog.add_task("压缩视频",total=sm)
        # prog.print("进度条右侧时间为不精确估算（当所有文件处理时间相同时估算精确）")
        # 使用 rglob 递归遍历所有文件
        for file in root_dir.rglob("*"):
            if file.parent.name == "compress":continue
            if file.is_file() and file.suffix.lower() in video_extensions:
                t = process_video(file)
                # if esti is not None:
                #     sm-=t
                #     prog.update(task,advance=1,description=f"预计剩余{fmt_time(sm)}")
                if t is None:
                    prog.advance(task)
                else:
                    prog.advance(task,t)

if __name__ == "__main__":
    setup_logging()
    tot_bgn = time()
    logging.info("-------------------------------")
    logging.info(datetime.now().strftime('Video Compress started at %Y/%m/%d %H:%M'))
    
    # 通过命令行参数传入需要遍历的目录
    if len(sys.argv) < 2:
        print(f"用法：python {__file__} <目标目录> [train]")
        logging.warning("Error termination via invalid input.")
        sys.exit(1)
    
    root = Path(sys.argv[1])
    if len(sys.argv) == 3:
        if sys.argv[2]=="train":
            train_init()
    else:
        if ESTI_FILE.exists():
            try:
                esti = np.fromfile(ESTI_FILE)
                # print(esti)
            except Exception:
                logging.warning(f"预测输出文件{str(ESTI_FILE)}存在但无法读取")
            
            
            
    if not root.is_dir():
        print("提供的路径不是一个有效目录。")
        logging.warning("Error termination via invalid input.")
        sys.exit(1)
    
    try:
        traverse_directory(root)
        tot_end = time()
        logging.info(f"Elapsed time: {fmt_time(tot_end-tot_bgn)}")
        logging.info("Normal termination of Video Compress.")
    except KeyboardInterrupt:
        logging.warning("Error termination via keyboard interrupt, CHECK IF LAST PROCSSING VIDEO IS COMPLETED.")
    except Exception as e:
        logging.error("Error termination via unhandled error, CHECK IF LAST PROCSSING VIDEO IS COMPLETED.",exc_info=e)
        
        
