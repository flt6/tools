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
TRAIN = False
ESTI_FILE = Path(sys.path[0])/"esti.out"
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
    "train": False
    
}
esti=None # :tuple[list[int],list[float]]

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
            "-vf", "scale=-1:1080",  
            "-c:v", CFG["codec"],
            "-b:v", CFG["bitrate"],
            "-r","30",
            "-y",
        ]
    else:
        command = [
            CFG["ffmpeg"],  
            "-hide_banner",
            "-i", video_path,
            "-vf", "scale=-1:1080",
            "-c:v", CFG["codec"],
            "-global_quality", str(CFG["crf"]),
            "-r","30",
            "-y",
        ]
    
    command.extend(CFG["extra"])
    command.append(output_file)
    return command

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

def polyfit_manual(x, y, degree=2):
    """手动实现二次多项式最小二乘拟合"""
    n = len(x)
    if n != len(y):
        raise ValueError("输入的x和y长度必须相同")
    
    # 对于二次多项式 y = ax^2 + bx + c
    # 构建矩阵方程 A * [a, b, c]^T = B
    # 其中 A = [[sum(x^4), sum(x^3), sum(x^2)], 
    #          [sum(x^3), sum(x^2), sum(x)], 
    #          [sum(x^2), sum(x), n]]
    # B = [sum(x^2 * y), sum(x * y), sum(y)]
    
    # 计算需要的和
    sum_x = sum(x)
    sum_x2 = sum(xi**2 for xi in x)
    sum_x3 = sum(xi**3 for xi in x)
    sum_x4 = sum(xi**4 for xi in x)
    sum_y = sum(y)
    sum_xy = sum(xi*yi for xi, yi in zip(x, y))
    sum_x2y = sum(xi**2*yi for xi, yi in zip(x, y))
    
    # 构建矩阵A和向量B
    A = [
        [sum_x4, sum_x3, sum_x2],
        [sum_x3, sum_x2, sum_x],
        [sum_x2, sum_x, n]
    ]
    B = [sum_x2y, sum_xy, sum_y]
    
    # 使用高斯消元法解线性方程组
    # 将增广矩阵 [A|B] 转换为行阶梯形式
    AB = [row + [b] for row, b in zip(A, B)]
    n_rows = len(AB)
    
    # 高斯消元
    for i in range(n_rows):
        # 寻找当前列中最大元素所在的行
        max_row = i
        for j in range(i + 1, n_rows):
            if abs(AB[j][i]) > abs(AB[max_row][i]):
                max_row = j
        
        # 交换行
        AB[i], AB[max_row] = AB[max_row], AB[i]
        
        # 将当前行主元归一化
        pivot = AB[i][i]
        if pivot == 0:
            raise ValueError("矩阵奇异，无法求解")
        
        for j in range(i, n_rows + 1):
            AB[i][j] /= pivot
        
        # 消元
        for j in range(n_rows):
            if j != i:
                factor = AB[j][i]
                for k in range(i, n_rows + 1):
                    AB[j][k] -= factor * AB[i][k]
    
    # 提取结果
    coeffs = [AB[i][n_rows] for i in range(n_rows)]
    
    return coeffs  # [a, b, c] 对应 ax^2 + bx + c

def save_esti():
    try:
        if len(esti_data[0]) > 0:
            coeffs = polyfit_manual(esti_data[0], esti_data[1])
            # 保存为逗号分隔的文本格式
            ESTI_FILE.write_text(','.join(map(str, coeffs)))
    except Exception as e:
        logging.warning("保存估算数据失败")
        logging.debug("error at save_esti",exc_info=e)

def fmt_time(t:float|int) -> str:
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
            coeffs = polyfit_manual(esti_data[0], esti_data[1])
            t = coeffs[0]*sz**2 + coeffs[1]*sz + coeffs[2]
        elif esti is not None:
            t = esti[0]*sz**2 + esti[1]*sz + esti[2]
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
        logging.warning("无法计算预计时间")
        logging.debug("esti time exception", exc_info=e)
        return -1 if src else "NaN"
    
def process_video(video_path: Path, compress_dir:Optional[Path]=None ,update_func=None):
    global esti_data
    use=None
    sz=video_path.stat().st_size//(1024*1024)
    # if esti is not None or TRAIN:
    #     use = func(sz,True)
    #     logging.info(f"开始处理文件: {video_path.relative_to(root)}，大小{sz}M，预计{fmt_time(use)}")
    # else:
    #     logging.info(f"开始处理文件: {video_path.relative_to(root)}，大小{sz}M")
        
    
    bgn=time()
    if compress_dir is None:
        # 在视频文件所在目录下创建 compress 子目录（如果不存在）
        compress_dir = video_path.parent / "compress"
    else:
        compress_dir /= video_path.parent.relative_to(root)
        
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
            
            end=time()
            if TRAIN:
                esti_data[0].append(sz)
                esti_data[1].append(end-bgn)
                
            
    except Exception as e:
        logging.error(f"执行 ffmpeg 命令时发生异常, 文件：{str(video_path_str)}，cmd={' '.join(map(str,command))}",exc_info=e)
    return use

def traverse_directory(root_dir: Path):
    video_extensions = set(CFG["video_ext"])
    sm=None
    if esti is not None:
        raise DeprecationWarning("不再支持训练模式")
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
    else:
        # logging.info("正在估算视频帧数，用于显示进度。")
        with Progress() as prog:
            task = prog.add_task("正在获取视频信息",total=len(list(root_dir.rglob("*"))))
            frames:dict[Path,float] = {}
            for file in root_dir.rglob("*"):
                prog.advance(task)
                if file.parent.name == "Compress":continue
                if file.is_file() and file.suffix.lower() in video_extensions:
                    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate,duration -of default=nokey=1:noprint_wrappers=1'.split()
                    cmd.append(str(file))
                    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if proc.returncode != 0:
                        logging.debug(f"无法获取视频信息: {file}, 返回码: {proc.returncode}")
                        logging.debug(proc.stdout)
                        logging.debug(proc.stderr)
                        frames[file] = 0
                        continue
                    if proc.stdout.strip():
                        avg_frame_rate, duration = proc.stdout.strip().split('\n')
                        tmp = avg_frame_rate.split('/')
                        avg_frame_rate = float(tmp[0]) / float(tmp[1])
                        if duration == "N/A":
                            duration = 0
                            logging.debug(f"无法获取视频信息: {file}, 时长为N/A，默认使用0s。运行时进度条将出现异常。")
                        duration = float(duration)
                        frames[file] = duration * avg_frame_rate
        
        
    logging.debug(f"开始遍历目录: {root_dir}")
    # 定义需要处理的视频后缀（忽略大小写）
    
    with Progress() as prog:
        task = prog.add_task("总进度",total=sm if sm is not None else sum(frames.values()))
        for file in frames.keys():
            # if "Compress" in file.relative_to(root_dir).parents:continue
            if file.is_file() and file.suffix.lower() in video_extensions:
                filename = file.relative_to(root_dir)
                if frames[file] == 0:
                    logging.warning("当前文件时长获取失败，进度条持续为0为正常现象。")
                    cur = prog.add_task(f"{filename}")
                else:
                    cur = prog.add_task(f"{filename}",total=frames[file])
                with prog._lock:
                    tmp = prog._tasks[task]
                    completed_start = tmp.completed
                    
                def update_progress(x):
                    if frames[file] == 0:
                        prog.update(cur,description=f"{filename} 已处理{x}帧")
                    else:
                        prog.update(cur,completed=x)
                        prog.update(task, completed=completed_start+x)
                
                if CFG["save_to"] == "single":
                    t = process_video(file, root_dir/"Compress", update_progress)
                else:
                    t = process_video(file, update_progress)
                    
                
                prog.stop_task(cur)
                prog.remove_task(cur)
                if t is None:
                    prog.update(task,completed=completed_start+frames[file])
                else:
                    prog.advance(task,t)

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
            "ffmpeg -hide_banner -f lavfi -i testsrc=duration=1:size=1920x1080:rate=30 -c:v libx264 -y -pix_fmt yuv420p compress_video_test.mp4".split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if ret.returncode != 0:
            logging.warning("无法生成测试视频.")
            logging.debug(ret.stdout)
            logging.debug(ret.stderr)
            ret.check_returncode()
        cmd = get_cmd("compress_video_test.mp4","compressed_video_test.mp4",)
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
    except Exception as e:
        if os.path.exists("compress_video_test.mp4"):
            os.remove("compress_video_test.mp4")
        logging.warning("测试未通过，继续运行可能出现未定义行为。")
        logging.debug("Test error",exc_info=e)

def init_train():
    global esti
    if CFG["train"]:
        train_init()
    else:
        if ESTI_FILE.exists():
            try:
                # 从文件读取系数
                coeffs_str = ESTI_FILE.read_text().strip().split(',')
                esti = [float(coeff) for coeff in coeffs_str]
            except Exception as e:
                logging.warning(f"预测输出文件{str(ESTI_FILE)}存在但无法读取", exc_info=e)

def exit_pause():
    if os.name == 'nt':
        os.system("pause")
    elif os.name == 'posix':
        os.system("read -p 'Press Enter to continue...'")

def main(_root = None):
    
    atexit.register(exit_pause)
    
    global root, esti
    setup_logging()
    tot_bgn = time()
    logging.info("-------------------------------")
    logging.info(datetime.now().strftime('Video Compress started at %Y/%m/%d %H:%M'))
    
    if CFG_FILE.exists():
        try:
            import json
            cfg:dict = json.loads(CFG_FILE.read_text())
            CFG.update(cfg)
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
    
    if root.name == "compress":
        logging.critical("请修改目标目录名为非compress。")
        logging.error("Error termination via invalid input.")
        sys.exit(1) 

    logging.info("开始验证环境")
    test()
    
    init_train()
    
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
