import subprocess
from pathlib import Path
import sys
import logging
from datetime import datetime
from time import time
import atexit

root = None
CODEC=None


# 配置logging
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"video_compress_{datetime.now().strftime('%Y%m%d')}.log"
    stream = logging.StreamHandler()
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

    
def process_video(video_path: Path):
    global esti_data
    use=None
    sz=video_path.stat().st_size//(1024*1024)
    logging.debug(f"开始处理文件: {video_path.relative_to(root)}，大小{sz}M")
        
    
    bgn=time()
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
    if CODEC=="h264_amf":
        command = [
            "ffmpeg.exe",  
            "-hide_banner",  # 隐藏 ffmpeg 的横幅信息
            "-i", str(video_path.absolute()),
            "-vf", "scale=-1:1080",  # 设置视频高度为 1080，宽度按比例自动计算
            "-c:v", CODEC,  # 使用 Intel Quick Sync Video 编码
            "-global_quality", "28",  # 设置全局质量（数值越低质量越高）
            "-c:a", "copy",  # 音频不做处理，直接拷贝
            "-r","30",
            "-y",
            str(output_file)
        ]
    else:
        command = [
            "ffmpeg.exe",  
            "-hide_banner",  # 隐藏 ffmpeg 的横幅信息
            "-i", str(video_path.absolute()),
            "-vf", "scale=-1:1080",  # 设置视频高度为 1080，宽度按比例自动计算
            "-c:v", CODEC,  # 使用 Intel Quick Sync Video 编码
            "-global_quality", "28",  # 设置全局质量（数值越低质量越高）
            "-c:a", "copy",  # 音频不做处理，直接拷贝
            "-r","30",
            "-preset", "slow", 
            "-y",
            str(output_file)
        ]
        
    
    try:
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding="utf-8", 
            text=True
        )
        
        if result.stderr:
            for line in result.stderr.splitlines():
                if 'warning' in line.lower():
                    logging.warning(f"[FFmpeg]({video_path}): {line}")
                elif 'error' in line.lower():
                    logging.error(f"[FFmpeg]({video_path}): {line}")
        
        if result.returncode != 0:
            logging.error(f"处理文件 {video_path} 失败，返回码: {result.returncode}，cmd={' '.join(command)}")
            logging.error(result.stdout)
            logging.error(result.stderr)
        else:
            logging.debug(f"文件处理成功: {video_path} -> {output_file}")
            
            end=time()
                
            
    except Exception as e:
        logging.error(f"执行 ffmpeg 命令时发生异常, 文件：{video_path}，cmd={' '.join(command)}",exc_info=e)
    return use

def traverse_directory(root_dir: Path):
    video_extensions = {".mp4", ".mkv"}
    sm=None
        
    logging.debug(f"开始遍历目录: {root_dir}")
    
    for file in root_dir.rglob("*"):
        if file.parent.name == "compress":continue
        if file.is_file() and file.suffix.lower() in video_extensions:
            t = process_video(file)

@atexit.register
def exit_handler():
    subprocess.run("pause", shell=True)

def _test():
    try:
        subprocess.run(f"ffmpeg -f lavfi -i testsrc=size=1280x720:rate=30 -t 1 -y  -c:v {CODEC} -pix_fmt yuv420p test.mp4",stdout=-3,stderr=-3).check_returncode()
        subprocess.run(f"ffmpeg -i test.mp4 -c:v {CODEC} -pix_fmt yuv420p -y  test2.mp4",stdout=-3,stderr=-3).check_returncode()
        return True
    except subprocess.CalledProcessError:
        return False
    finally:
        Path("test.mp4").unlink(True)
        Path("test2.mp4").unlink(True)    

if __name__ == "__main__":
    setup_logging()
    tot_bgn = time()
    logging.info("-------------------------------")
    logging.info(datetime.now().strftime('Video Compress started at %Y/%m/%d %H:%M'))
    
    try:
        subprocess.run("ffmpeg.exe -version",stdout=-3,stderr=-3).check_returncode()
    except subprocess.CalledProcessError:
        logging.critical("FFmpeg 未安装或不在系统 PATH 中。")
        sys.exit(1)
    
    
    if len(sys.argv) < 2:
        print(f"推荐用法：python {__file__} <目标目录>")
        root = Path(input("请输入目标目录："))
        while not root.is_dir():
            root = Path(input("请输入目标目录："))
    else:
        root = Path(sys.argv[1])
        if len(sys.argv) == 3:
            CODEC=sys.argv[2]
            logging.info(f"使用编码器因为cmd：{CODEC}")
        if not root.is_dir():
            print("提供的路径不是一个有效目录。")
            logging.warning("Error termination via invalid input.")
            sys.exit(1)
    
    if CODEC is None:
        logging.info("检测可用编码器")
        try:
            ret = subprocess.run(["ffmpeg","-codecs"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            ret.check_returncode()
            avai = []
            if "cuda" in ret.stdout:avai.append("cuda")
            if "amf" in ret.stdout:avai.append("amf")
            if "qsv" in ret.stdout:avai.append("qsv")
            avai.append("h264")
            
            for c in avai:
                CODEC = "h264_" + c
                if _test():
                    break
            if not _test:
                logging.critical("没有可用的h264编码器。")
                exit(1)
        except Exception as e:
            logging.error("Error termination via unhandled error.",exc_info=e)
        finally:
            logging.info(f"使用编码器：{CODEC}")
    
    try:
        traverse_directory(root)
        tot_end = time()
        logging.info(f"Elapsed time: {(tot_end-tot_bgn)}s")
        logging.info("Normal termination of Video Compress.")
    except KeyboardInterrupt:
        logging.warning("Error termination via keyboard interrupt, CHECK IF LAST PROCSSING VIDEO IS COMPLETED.")
    except Exception as e:
        logging.error("Error termination via unhandled error, CHECK IF LAST PROCSSING VIDEO IS COMPLETED.",exc_info=e)
        
        
