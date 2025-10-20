import subprocess
from pathlib import Path
import sys
import os
import logging
from datetime import datetime
from time import time
from rich.logging import RichHandler
from rich.progress import Progress
from pickle import dumps, loads
from typing import Optional
import atexit
import re

root = None
CFG_FILE = Path(sys.path[0])/"config.json"
CFG = {
    "save_to": "single",
    "crf":"18",
    "bitrate": None,
    "codec": "h264",
    "extra": [],
    "ffmpeg": "ffmpeg",
    "manual": None,
    "video_ext": [".mp4", ".mkv"],
    "compress_dir_name": "compress",
    "resolution": "-1:1080",
    "fps": "30",
    "test_video_resolution": "1920x1080",
    "test_video_fps": "30",
    "test_video_input": "compress_video_test.mp4",
    "test_video_output": "compressed_video_test.mp4",
}


def get_cmd(video_path,output_file):
    if CFG["manual"] is not None:
        command=[
            CFG["ffmpeg"],  
            "-hide_banner", 
            "-i", video_path
        ]
        command.extend(CFG["manual"])
        command.append(output_file)
        return command
    
    if CFG["bitrate"] is not None:
        command = [
            CFG["ffmpeg"],  
            "-hide_banner",
            "-i", video_path,
        ]
        if CFG['resolution'] is not None:
            command.extend([
            "-vf", f"scale={CFG['resolution']}",])
        command.extend([
            "-c:v", CFG["codec"],
            "-b:v", CFG["bitrate"],
            "-r",CFG["fps"],
            "-y",
        ])
    else:
        command = [
            CFG["ffmpeg"],  
            "-hide_banner",
            "-i", video_path,
            ]
        if CFG['resolution'] is not None:
            command.extend([
            "-vf", f"scale={CFG['resolution']}",])
        command.extend([
            "-c:v", CFG["codec"],
            "-global_quality", str(CFG["crf"]),
            "-r",CFG["fps"],
            "-y",
        ])
    
    command.extend(CFG["extra"])
    command.append(output_file)
    logging.debug(f"Create CMD: {command}")
    return command



# 配置logging
def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"video_compress_{datetime.now().strftime('%Y%m%d')}.log"
    stream = RichHandler(rich_tracebacks=True,tracebacks_show_locals=True)
    stream.setLevel(logging.INFO)
    stream.setFormatter(logging.Formatter("%(message)s"))
    
    file = logging.FileHandler(log_file, encoding='utf-8')
    file.setLevel(logging.DEBUG)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname) 7s - %(message)s',
        handlers=[
            file,
            stream
        ]
    )

def fmt_time(t:float|int) -> str:
    if t>3600:
        return f"{t//3600}h {t//60}min {t%60}s"
    elif t>60:
        return f"{t//60}min {t%60}s"
    else:
        return f"{round(t)}s"

def process_video(video_path: Path, compress_dir:Optional[Path]=None ,update_func=None):
    use=None
    sz=video_path.stat().st_size//(1024*1024)
    
    if compress_dir is None:
        # 在视频文件所在目录下创建 compress 子目录（如果不存在）
        compress_dir = video_path.parent / CFG["compress_dir_name"]
    else:
        compress_dir /= video_path.parent.relative_to(root)
    
    assert isinstance(compress_dir,Path)
    compress_dir.mkdir(exist_ok=True,parents=True)
    
    # 输出文件路径：与原文件同名，保存在 compress 目录下
    output_file = compress_dir / (video_path.stem + video_path.suffix)
    if output_file.is_file():
        logging.warning(f"文件{output_file}存在，跳过")
        return use
    
    video_path_str = str(video_path.absolute())
    command = get_cmd(video_path_str,output_file)
    
    try:
        result = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding="utf-8", 
            text=True
        )
        
        while result.poll() is None:
            line = " "
            while result.poll() is None and line[-1:] not in "\r\n":
                line+=result.stderr.read(1)
                # print(line[-1])
            if 'warning' in line.lower():
                logging.warning(f"[FFmpeg]({video_path_str}): {line}")
            elif 'error' in line.lower():
                logging.error(f"[FFmpeg]({video_path_str}): {line}")
            elif "frame=" in line:
                # print(line,end="")
                match = re.search(r"frame=\s*(\d+)",line)
                if match:
                    frame_number = int(match.group(1))
                    if update_func is not None:
                        update_func(frame_number)

        if result.returncode != 0:
            logging.error(f"处理文件 {video_path_str} 失败，返回码: {result.returncode}，cmd={' '.join(command)}")
            logging.error(result.stdout)
            logging.error(result.stderr)
        else:
            logging.debug(f"文件处理成功: {video_path_str} -> {output_file}")
            
    except KeyboardInterrupt as e:raise e
    except Exception as e:
        logging.error(f"执行 ffmpeg 命令时发生异常, 文件：{str(video_path_str)}，cmd={' '.join(map(str,command))}",exc_info=e)
    return use

def traverse_directory(root_dir: Path):
    video_extensions = set(CFG["video_ext"])
    sm=None
    # 获取视频文件列表和帧数信息
    video_files = []
    que = list(root_dir.glob("*"))
    while que:
        d = que.pop()
        for file in d.glob("*") if d.is_dir() else [d]:
            if file.parent.name == CFG["compress_dir_name"] or file.name == CFG["compress_dir_name"]:
                continue
            if file.is_file() and file.suffix.lower() in video_extensions:
                video_files.append(file)
            elif file.is_dir():
                que.append(file)


        if not video_files:
            logging.warning("未找到需要处理的视频文件")
            return

    # 获取视频信息
    frames: dict[Path, float] = {}
    info_file = Path("video_info.cache")
    if info_file.is_file():
        try:
            cached_data = loads(info_file.read_bytes())
            if isinstance(cached_data, dict):
                frames = cached_data
                logging.debug("Loaded video info from cache.")
        except Exception as e:
            logging.debug("Failed to load video info cache.",exc_info=e)
    
    with Progress() as prog:
        task = prog.add_task("正在获取视频信息", total=len(video_files))
        for file in video_files:
            prog.advance(task)
            if file in frames and frames[file]>0:
                continue
            cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate,duration -of default=nokey=1:noprint_wrappers=1'.split()
            cmd.append(str(file.resolve()))
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logging.debug(f"无法获取视频信息: {file}, 返回码: {proc.returncode}")
                frames[file] = 0
                continue
            if proc.stdout.strip():
                try:
                    avg_frame_rate, duration = proc.stdout.strip().split('\n')
                    tmp = avg_frame_rate.split('/')
                    avg_frame_rate = float(tmp[0]) / float(tmp[1])
                    if duration == "N/A":
                        duration = 0
                        logging.debug(f"无法获取视频信息: {file}, 时长为N/A，默认使用0s")
                    duration = float(duration)
                    frames[file] = duration * avg_frame_rate
                except (ValueError, IndexError) as e:
                    logging.debug(f"解析视频信息失败: {file}, 错误: {e}")
                    frames[file] = 0
        if 0 in frames.values():
            logging.warning(f"视频{', '.join([f.name for f,frames in frames.items() if frames==0])}文件帧数信息获取失败。总进度估计将不准确。")
    try:
        info_file.write_bytes(dumps(frames))
        logging.debug("Saved video info to cache.")
    except Exception as e:
        logging.debug("Failed to save video info cache.",exc_info=e)

    logging.debug(f"开始遍历目录: {root_dir}, 共{len(frames)}个视频文件")
    
    
    # 创建进度条
    with Progress() as prog:
        total_frames = sum(frames.values())
        main_task = prog.add_task("总进度", total=total_frames if total_frames > 0 else len(frames))
        
        # 创建文件队列
        for file in frames.keys():
            # 进度跟踪
            filename = file.relative_to(root_dir)
            
            # 创建文件级进度条
            if frames[file] == 0:
                file_task = prog.add_task(f"{filename}")
            else:
                file_task = prog.add_task(f"{filename}",total=frames[file])
            
            
            with prog._lock:
                completed_start = prog._tasks[main_task].completed
                
            def update_progress(x):
                if frames[file] == 0:
                    prog.update(file_task,description=f"{filename} 已处理{x}帧")
                else:
                    prog.update(file_task,completed=x)
                    prog.update(main_task, completed=completed_start+x)
            
            if CFG["save_to"] == "single":
                process_video(file, root_dir/"Compress", update_progress)
            else:
                process_video(file, None, update_progress)

            # 移除文件级进度条
            prog.remove_task(file_task)
    
    try:
        info_file.unlink(missing_ok=True)
    except Exception as e:
        logging.warning("无法删除视频信息缓存文件",exc_info=e)

def test():
    os.environ["PATH"] = Path(__file__).parent.as_posix() + os.pathsep + os.environ["PATH"]

    try:
        subprocess.run([CFG["ffmpeg"],"-version"],stdout=-3,stderr=-3).check_returncode()
    except Exception as e:
        print(__file__)
        logging.critical("无法运行ffmpeg")
        exit(-1)
    try:
        ret = subprocess.run(
            f"ffmpeg -hide_banner -f lavfi -i testsrc=duration=1:size={CFG['test_video_resolution']}:rate={CFG['test_video_fps']} -c:v libx264 -y -pix_fmt yuv420p {CFG['test_video_input']}".split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if ret.returncode != 0:
            logging.warning("无法生成测试视频.")
            logging.debug(ret.stdout)
            logging.debug(ret.stderr)
            ret.check_returncode()
        cmd = get_cmd(CFG["test_video_input"],CFG["test_video_output"],)
        ret = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if ret.returncode != 0:
            logging.error("测试视频压缩失败")
            logging.debug(ret.stdout)
            logging.debug(ret.stderr)
            logging.error("Error termination via test failed.")
            exit(-1)
        os.remove("compress_video_test.mp4")
        os.remove("compressed_video_test.mp4")
    except KeyboardInterrupt as e:raise e
    except Exception as e:
        if os.path.exists("compress_video_test.mp4"):
            os.remove("compress_video_test.mp4")
        logging.warning("测试未通过，继续运行可能出现未定义行为。")
        logging.debug("Test error",exc_info=e)


def exit_pause():
    if os.name == 'nt':
        os.system("pause")
    elif os.name == 'posix':
        os.system("read -p 'Press Enter to continue...'")

def main(_root = None):
    
    atexit.register(exit_pause)
    
    global root
    setup_logging()
    tot_bgn = time()
    logging.info("-------------------------------")
    logging.info(datetime.now().strftime('Video Compress started at %Y/%m/%d %H:%M'))
    
    if CFG_FILE.exists():
        try:
            import json
            cfg:dict = json.loads(CFG_FILE.read_text())
            CFG.update(cfg)
        except KeyboardInterrupt as e:raise e
        except Exception as e:
            logging.warning("Invalid config file, ignored.")
            logging.debug(e)
    
    if _root is not None:
        root = Path(_root)
    else:
        # 通过命令行参数传入需要遍历的目录
        if len(sys.argv) < 2:
            print(f"用法：python {__file__} <目标目录>")
            logging.warning("Error termination via invalid input.")
            sys.exit(1)
        root = Path(sys.argv[1])
    
    if root.name.lower() == CFG["compress_dir_name"].lower():
        logging.critical("请修改目标目录名为非compress。")
        logging.error("Error termination via invalid input.")
        sys.exit(1) 

    logging.info("开始验证环境")
    test()
    
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

if __name__ == "__main__":
    main()
