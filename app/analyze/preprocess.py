# app/analyze/video.py
import json
import shutil
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────
# 최소/안전 버전: 항상 재인코딩해서 30fps/720p(+선택적 미러)
# ─────────────────────────────────────────────────────────
def normalize_video(src: str, dst: str, fps: int, height: int, mirror: bool = False):
    """
    가장 단순하고 안전한 표준화:
    - VFR 입력도 CFR로 강제(fps 필터)
    - 세로 height 고정, 가로는 비율 유지(-2로 짝수 보장)
    - 오디오는 제거(-an) → 분석용 용량/속도 최적화
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH. Please install ffmpeg.")

    vf = [f"fps={fps}", f"scale=-2:{height}"]
    if mirror:
        vf.append("hflip")

    cmd = [
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-i", src,
        "-vf", ",".join(vf),
        "-an",
        "-pix_fmt", "yuv420p",      # 모바일/웹 호환↑
        "-movflags", "+faststart",  # 스트리밍/프리뷰 시작 빠르게
        dst
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────
# ffprobe 헬퍼: 원본 메타데이터(폭/높이/길이/FPS 등) 확인
# ─────────────────────────────────────────────────────────
def probe_video_meta(path: str) -> dict:
    if shutil.which("ffprobe") is None:
        return {}
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams", "-select_streams", "v:0",
        "-show_format",
        path
    ])
    info = json.loads(out)
    st = info.get("streams", [{}])[0]
    fmt = info.get("format", {})
    # FPS 파싱 (예: '30000/1001' → 29.97)
    fr = st.get("avg_frame_rate", "0/1")
    try:
        num, den = fr.split("/")
        fps = float(num) / float(den) if float(den) != 0 else None
    except Exception:
        fps = None

    return {
        "width":  int(st.get("width") or 0) or None,
        "height": int(st.get("height") or 0) or None,
        "duration": float(fmt.get("duration")) if fmt.get("duration") else None,
        "fps": fps
    }


# ─────────────────────────────────────────────────────────
# 프로 버전: 하드웨어 인코딩/품질/속도 튜닝 + smart copy
# ─────────────────────────────────────────────────────────
def _run(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}") from e

def normalize_video_pro(
    src: str,
    dst: str,
    fps: int,
    height: int,
    mirror: bool = False,
    *,
    codec: str = "libx264",        # mac: "h264_videotoolbox" 추천(하드웨어 인코딩)
    crf: int = 22,                 # 낮을수록 고화질(용량↑). 18~24 권장
    preset: str = "veryfast",      # slower=느리지만 더 좋게 압축, veryfast=빠름
    keep_audio: bool = False,      # 분석엔 보통 False
    smart_copy: bool = True        # 이미 규격이면 컨테이너만 재작성
) -> dict:
    """
    반환: {"mode": "copy" | "encode", "ms": 처리시간(ms)} (로깅/모니터링용)
    """
    import time
    t0 = time.perf_counter()

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH.")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe not found in PATH.")

    dst_p = Path(dst); dst_p.parent.mkdir(parents=True, exist_ok=True)

    meta = probe_video_meta(src)
    src_h = meta.get("height")
    src_fps = meta.get("fps")

    # smart copy 조건(엄격 CFR 필요하면 비활성 권장)
    close_fps = (src_fps is not None) and (abs(src_fps - fps) < 0.1)
    same_h = (src_h is not None) and (src_h == height)
    if smart_copy and close_fps and same_h and not mirror and keep_audio:
        _run([
            "ffmpeg","-y","-hide_banner","-loglevel","error",
            "-i", src,
            "-c", "copy",
            "-movflags","+faststart",
            str(dst_p)
        ])
        return {"mode": "copy", "ms": int((time.perf_counter()-t0)*1000)}

    # 재인코딩 경로(정석)
    vf = [f"fps={fps}", f"scale=-2:{height}"]
    if mirror:
        vf.append("hflip")

    cmd = [
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-i", src,
        "-vf", ",".join(vf),
        "-c:v", codec,
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-g", str(fps*2),  # 키프레임 간격 ~2초
    ]
    if keep_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-an"]

    cmd += [str(dst_p)]
    _run(cmd)
    return {"mode": "encode", "ms": int((time.perf_counter()-t0)*1000)}