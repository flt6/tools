import subprocess
from pathlib import Path
import sys
import os
import logging
from datetime import datetime
from time import time
from rich.logging import RichHandler
from rich.progress import Progress
from typing import Optional
import atexit
import re
import threading
import queue
import psutil

root = None
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
    "max_concurrent_instances": 2,
    "cpu_monitor_interval": 3,  # CPU监控间隔（秒）
    "cpu_monitor_duration": 30,  # 统计持续时间（秒，5分钟）
}

# CPU监控相关全局变量
ffmpeg_processes = {}  # 存储活动的ffmpeg进程
cpu_stats = {"system": [], "ffmpeg": []}  # CPU使用率统计
cpu_monitor_thread = None
cpu_monitor_lock = threading.Lock()
current_instances = 0
instance_lock = threading.Lock()

def get_config_path() -> Path:
    """获取配置文件路径"""
    if os.environ.get("INSTALL", "0") == "1":
        return Path(os.getenv("APPDATA", "C:/")) / "VideoCompress" / "config.json"
    else:
        return Path("config.json").resolve()

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

def cpu_monitor():
    """CPU监控线程函数"""
    global cpu_stats
    
    while True:
        try:
            # 获取系统CPU使用率
            system_cpu = psutil.cpu_percent(interval=1)
            
            # 获取所有ffmpeg进程的CPU使用率
            ffmpeg_cpu_total = 0
            active_processes = []
            
            with cpu_monitor_lock:
                for proc_info in ffmpeg_processes.values():
                    try:
                        proc = proc_info['process']
                        if proc.is_running():
                            # print(proc,proc.cpu_percent() / psutil.cpu_count())
                            ffmpeg_cpu_total += proc.cpu_percent() / psutil.cpu_count()
                            active_processes.append(proc_info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # 更新统计数据
            with cpu_monitor_lock:
                cpu_stats["system"].append(system_cpu)
                cpu_stats["ffmpeg"].append(ffmpeg_cpu_total)
                
                # 保持最近5分钟的数据
                max_samples = CFG["cpu_monitor_duration"] // CFG["cpu_monitor_interval"]
                if len(cpu_stats["system"]) > max_samples:
                    cpu_stats["system"] = cpu_stats["system"][-max_samples:]
                if len(cpu_stats["ffmpeg"]) > max_samples:
                    cpu_stats["ffmpeg"] = cpu_stats["ffmpeg"][-max_samples:]
            
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logging.error(f"CPU监控异常: {e}")
        
        # 等待下一次监控
        threading.Event().wait(CFG["cpu_monitor_interval"])

def start_cpu_monitor():
    """启动CPU监控线程"""
    global cpu_monitor_thread
    if cpu_monitor_thread is None or not cpu_monitor_thread.is_alive():
        cpu_monitor_thread = threading.Thread(target=cpu_monitor, daemon=True)
        cpu_monitor_thread.start()
        logging.info("CPU监控线程已启动")

def get_cpu_usage_stats():
    """获取CPU使用率统计"""
    with cpu_monitor_lock:
        if not cpu_stats["system"] or not cpu_stats["ffmpeg"]:
            return None, None
        
        system_avg = sum(cpu_stats["system"]) / len(cpu_stats["system"])
        ffmpeg_avg = sum(cpu_stats["ffmpeg"]) / len(cpu_stats["ffmpeg"])
        
    return system_avg, ffmpeg_avg

def should_increase_instances():
    """判断是否应该增加实例数"""
    system_avg, ffmpeg_avg = get_cpu_usage_stats()
    
    if system_avg is None or ffmpeg_avg is None:
        return False
    
    # 条件: 系统CPU - FFmpeg CPU > FFmpeg CPU * 2 + 0.1
    available_cpu = 100 - system_avg
    threshold = ffmpeg_avg  # 10% = 0.1 * 100
    
    logging.debug(f"CPU统计: 系统平均={system_avg:.1f}%, FFmpeg平均={ffmpeg_avg:.1f}%, 可用={available_cpu:.1f}%, 阈值={threshold:.1f}%")
    
    return available_cpu > threshold

def register_ffmpeg_process(proc_id, process):
    """注册ffmpeg进程用于监控"""
    with cpu_monitor_lock:
        ffmpeg_processes[proc_id] = {
            'process': psutil.Process(process.pid),
            'start_time': time()
        }

def unregister_ffmpeg_process(proc_id):
    """注销ffmpeg进程"""
    with cpu_monitor_lock:
        if proc_id in ffmpeg_processes:
            del ffmpeg_processes[proc_id]

def process_video(video_path: Path, compress_dir:Optional[Path]=None, update_func=None, proc_id=None):
    global current_instances
    use=None
    sz=video_path.stat().st_size//(1024*1024)
    
    bgn=time()
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
        with instance_lock:
            current_instances += 1
        
        logging.debug(f"启动FFmpeg进程 {proc_id}: {video_path.name}")
        
        result = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding="utf-8", 
            text=True
        )
        
        # 注册进程用于CPU监控
        if proc_id:
            register_ffmpeg_process(proc_id, result)
        
        while result.poll() is None:
            line = " "
            while result.poll() is None and line[-1:] not in "\r\n":
                line+=result.stderr.read(1)
            if 'warning' in line.lower():
                logging.warning(f"[FFmpeg {proc_id}]({video_path_str}): {line}")
            elif 'error' in line.lower():
                logging.error(f"[FFmpeg {proc_id}]({video_path_str}): {line}")
            elif "frame=" in line:
                match = re.search(r"frame=\s*(\d+)",line)
                if match:
                    frame_number = int(match.group(1))
                    if update_func is not None:
                        update_func(frame_number)

        if result.returncode != 0:
            logging.error(f"处理文件 {video_path_str} 失败，返回码: {result.returncode}，cmd={' '.join(map(str,command))}")
            logging.error(result.stdout.read())
            logging.error(result.stderr.read())
        else:
            logging.debug(f"文件处理成功: {video_path_str} -> {output_file}")
            
    except KeyboardInterrupt as e:raise e
    except Exception as e:
        logging.error(f"执行 ffmpeg 命令时发生异常, 文件：{str(video_path_str)}，cmd={' '.join(map(str,command))}",exc_info=e)
    finally:
        # 注销进程监控
        if proc_id:
            unregister_ffmpeg_process(proc_id)
        
        with instance_lock:
            current_instances -= 1
            
        logging.debug(f"FFmpeg进程 {proc_id} 已结束")
        
    return use

def traverse_directory(root_dir: Path):
    global current_instances
    video_extensions = set(CFG["video_ext"])
    # 获取视频文件列表和帧数信息
    video_files = []
    que = [root_dir]
    while que:
        d = que.pop()
        for file in d.glob("*"):
            if file.parent.name == CFG["compress_dir_name"] or file.name == CFG["compress_dir_name"]:
                continue
            if file.is_file() and file.suffix.lower() in video_extensions:
                video_files.append(file)
            elif file.is_dir():
                que.append(file)
                
            
        # exit()
        
    if not video_files:
        logging.warning("未找到需要处理的视频文件")
        return
        
    # 获取视频信息
    with Progress() as prog:
        task = prog.add_task("正在获取视频信息", total=len(video_files))
        frames: dict[Path, float] = {}
        for file in video_files:
            prog.advance(task)
            cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate,duration -of default=nokey=1:noprint_wrappers=1'.split()
            cmd.append(str(file))
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
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
    
    logging.debug(f"开始遍历目录: {root_dir}, 共{len(frames)}个视频文件")
    
    # 启动CPU监控
    start_cpu_monitor()
    
    # 创建进度条
    with Progress() as prog:
        total_frames = sum(frames.values())
        main_task = prog.add_task("总进度", total=total_frames if total_frames > 0 else len(frames))
        
        # 创建文件队列
        file_queue = queue.Queue()
        for file in frames.keys():
            file_queue.put(file)
        
        # 进度跟踪
        progress_trackers = {}
        completed_files = 0
        total_completed_frames = 0
        
        def create_progress_updater(file_path, task_id):
            def update_progress(frame_count):
                nonlocal total_completed_frames
                if file_path in progress_trackers:
                    old_frames = progress_trackers[file_path]
                    diff = frame_count - old_frames
                    total_completed_frames += diff
                else:
                    total_completed_frames += frame_count
                progress_trackers[file_path] = frame_count
                
                if frames[file_path] > 0:
                    prog.update(task_id, completed=frame_count)
                else:
                    prog.update(task_id, description=f"{file_path.relative_to(root_dir)} 已处理{frame_count}帧")
                
                # 更新总进度
                if total_frames > 0:
                    prog.update(main_task, completed=total_completed_frames)
            return update_progress
        
        def process_file_worker():
            nonlocal completed_files
            while True:
                try:
                    file = file_queue.get(timeout=1)
                except queue.Empty:
                    break
                
                filename = file.relative_to(root_dir)
                
                # 创建文件级进度条
                if frames[file] == 0:
                    file_task = prog.add_task(f"{filename}")
                else:
                    file_task = prog.add_task(f"{filename}", total=frames[file])
                
                progress_updater = create_progress_updater(file, file_task)
                
                # 处理视频
                proc_id = f"worker_{threading.current_thread().ident}_{completed_files}"
                
                if CFG["save_to"] == "single":
                    process_video(file, root_dir/"Compress", progress_updater, proc_id)
                else:
                    process_video(file, None, progress_updater, proc_id)
                
                # 更新完成计数
                with instance_lock:
                    completed_files += 1
                    if total_frames == 0:  # 如果没有总帧数，按文件数计算
                        prog.update(main_task, completed=completed_files)
                
                # 移除文件级进度条
                prog.remove_task(file_task)
                file_queue.task_done()
        
        # 动态管理线程数
        active_threads = []
        max_workers = CFG["max_concurrent_instances"]
        
        def manage_workers():
            nonlocal active_threads
            
            while completed_files < len(frames) or any(t.is_alive() for t in active_threads):
                # 清理已完成的线程
                active_threads = [t for t in active_threads if t.is_alive()]
                
                # 检查是否需要增加实例
                current_worker_count = len(active_threads)
                
                if current_worker_count < max_workers and not file_queue.empty():
                    # 检查CPU使用率（运行5分钟后开始检查）
                    should_add_worker = False
                    if len(cpu_stats["system"]) >= 10:  # 至少有5分钟的数据
                        if current_worker_count >= 1:  # 已有实例运行
                            should_add_worker = should_increase_instances()
                            if should_add_worker:
                                logging.info("CPU资源充足，启动第二个压缩实例")
                            else:
                                should_add_worker = False
                    
                    if should_add_worker:
                        worker_thread = threading.Thread(target=process_file_worker, daemon=True)
                        worker_thread.start()
                        active_threads.append(worker_thread)
                        logging.debug(f"启动新的工作线程，当前活动线程数: {len(active_threads)}")
                
                threading.Event().wait(5)  # 每5秒检查一次
            
            # 等待所有线程完成
            for thread in active_threads:
                thread.join()
        
        # 启动第一个工作线程
        if not file_queue.empty():
            first_worker = threading.Thread(target=process_file_worker, daemon=True)
            first_worker.start()
            active_threads.append(first_worker)
            logging.info("启动第一个压缩实例")
            
            # 启动线程管理器
            manager_thread = threading.Thread(target=manage_workers, daemon=True)
            manager_thread.start()
            
            # 等待管理线程完成
            manager_thread.join()
    
    logging.info(f"所有视频处理完成，共处理了 {completed_files} 个文件")

def test():
    os.environ["PATH"] = Path(__file__).parent.as_posix() + os.pathsep + os.environ["PATH"]

    try:
        subprocess.run([CFG["ffmpeg"],"-version"],stdout=-3,stderr=-3).check_returncode()
    except KeyboardInterrupt as e:raise e
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
    
    if get_config_path().exists():
        try:
            import json
            cfg:dict = json.loads(get_config_path().read_text())
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
