import json
import logging
import subprocess
from fractions import Fraction
from decimal import Decimal
from typing import Optional, Tuple

ffprobe:str = "ffprobe"
class FFProbeError(RuntimeError):
    pass

def _run_ffprobe(args: list[str]) -> dict:
    """运行 ffprobe 并以 JSON 返回，若失败抛异常。"""
    # 始终要求 JSON 输出，便于稳健解析
    base = [ffprobe, "-v", "error", "-print_format", "json"]
    proc = subprocess.run(base + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise FFProbeError(proc.stderr.strip() or "ffprobe 调用失败")
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        raise FFProbeError(f"无法解析 ffprobe 输出为 JSON: {e}")

def _try_nb_frames(path: str, stream_index: int) -> Optional[int]:
    data = _run_ffprobe([
        "-select_streams", f"v:{stream_index}",
        "-show_entries", "stream=nb_frames",
        path
    ])
    streams = data.get("streams") or []
    if not streams:
        logging.debug("_try_nb_frames: failed no stream")
        return None
    nb = streams[0].get("nb_frames")
    if nb and nb != "N/A":
        try:
            n = int(nb)
            return n if n >= 0 else None
        except ValueError:
            logging.debug(f"_try_nb_frames: failed nb not positive int: {nb}")
            return None
    logging.debug(f"_try_nb_frames: failed nb NA: {nb}")
    return None

def _try_avgfps_times_duration(path: str, stream_index: int) -> Optional[int]:
    # 读 avg_frame_rate
    s = _run_ffprobe([
        "-select_streams", f"v:{stream_index}",
        "-show_entries", "stream=avg_frame_rate",
        path
    ])
    streams = s.get("streams") or []
    if not streams:
        return None
    afr = streams[0].get("avg_frame_rate")
    if not afr or afr in ("0/0", "N/A"):
        return None

    # 读容器时长（单位：秒）
    f = _run_ffprobe(["-show_entries", "format=duration", path])
    dur_str = (f.get("format") or {}).get("duration")
    if not dur_str:
        logging.debug(f"_try_avgfps_times_duration: failed no dur_str, {f}")
        return None

    try:
        fps = Fraction(afr)  # 形如 "30000/1001"
        dur = Decimal(dur_str)
        # 四舍五入到最近整数，避免系统性低估
        est = int(dur * Decimal(fps.numerator) / Decimal(fps.denominator) + Decimal("0.5"))
        return est if est >= 0 else None
    except Exception as e:
        logging.debug("_try_avgfps_times_duration: failed",exc_info=e)
        return None

def _try_count_packets(path: str, stream_index: int) -> Optional[int]:
    # 统计读取到的包数（不解码）。大多容器≈帧数，但不保证 1:1
    data = _run_ffprobe([
        "-select_streams", f"v:{stream_index}",
        "-count_packets",
        "-show_entries", "stream=nb_read_packets",
        path
    ])
    streams = data.get("streams") or []
    if not streams:
        logging.debug("_try_count_packets: failed no stream")
        return None
    nbp = streams[0].get("nb_read_packets")
    try:
        n = int(nbp)
        return n if n >= 0 else None
    except Exception as e:
        logging.debug("_try_count_packets: failed",exc_info=e)
        return None

def get_video_frame_count(
    path: str,
    stream_index: int = 0,
    fallback_order: Tuple[str, ...] = ("nb_frames", "avg*dur", "count_packets"),
) -> int|None:
    """
    估计/获取视频总帧数（带回退）。
    参数:
      - path: 视频文件路径
      - stream_index: 选择哪个视频流，默认 0
      - allow_slow_decode: 是否允许用解码全片的方式（最慢但最准）
      - fallback_order: 回退顺序，四种方法的别名可选：
            "nb_frames"   -> 直接读元数据中的总帧数
            "avg*dur"     -> 平均帧率 × 时长（最快估算）
            "count_packets" -> 统计包数（较快，接近帧数但不保证）
    返回:
      (frame_count, method_used)
    异常:
      - FileNotFoundError: ffprobe 未安装
      - FFProbeError: ffprobe 调用异常或无法解析
      - RuntimeError: 所有方法均失败
    """
    methods = {
        "nb_frames": _try_nb_frames,
        "avg*dur": _try_avgfps_times_duration,
        "count_packets": _try_count_packets,
    }

    for key in fallback_order:
        try:
            func = methods.get(key)
            if not func:
                continue
            n = func(path, stream_index)
            if isinstance(n, int) and n >= 0:
                return n
            else:
                logging.debug(f"Failed to get frame with {key}")
        except Exception as e:
            logging.debug(f"Errored to get frame with {key}.",exc_info=e)

    return None
    raise RuntimeError("无法获取或估计帧数：所有回退方法均失败。")
