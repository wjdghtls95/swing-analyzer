import argparse, csv, json, os
from pathlib import Path
import requests

# tqdm이 없을 때는 tqdm()을 그냥 무시하는 함수로 바꾸는 try except
try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **k: x

# 앱 서버 엔드포인트
API = os.getenv("ANALYZE_API", "http://127.0.0.1:8080/analyze")

# youtube url 로 뽑은 manifest 로 실행
def iter_from_manifest(manifest_path: Path):
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in data:
        yield (item["path"], item.get("pro") or item.get("athlete", "unknown"), item.get("club", "unknown"))

# 직접 다운로드 받은 mp4 파일을 실행
def iter_from_root(root: Path):
    # data/raw/pros/<athlete>/<club>/*.mp4 or data/videos/pros_faceon/<athlete>/<club>/*.mp4
    for p in root.rglob("*.mp4"):
        parts = p.parts
        athlete, club = "unknown", "unknown"
        # …/<pros|pros_faceon>/<athlete>/<club>/<file>
        for i, name in enumerate(parts):
            if name in ("pros", "pros_faceon") and i + 2 < len(parts):
                athlete = parts[i+1]
                club = parts[i+2]
                break
        yield (str(p), athlete, club)

def analyze_one(video_path: str, club: str, side: str, min_vis: float, norm_mode: str, timeout: int):
    with open(video_path, "rb") as f:
        files = {"file": f}
        params = {"side": side, "min_vis": min_vis, "norm_mode": norm_mode, "club": club}
        r = requests.post(API, params=params, files=files, timeout=timeout)
    r.raise_for_status()
    return r.json()

def main():
    ap = argparse.ArgumentParser(description="Videos -> /analyze -> phase_dataset.csv")
    ap.add_argument("--manifest", type=str, help="manifest.json (pro, club, path 목록)")
    ap.add_argument("--root", type=str, help="영상이 들어있는 루트 디렉토리 (manifest 없을 때 폴더 스캔)")
    ap.add_argument("--out", default="data/processed/phase_dataset.csv")
    ap.add_argument("--side", default="right")
    ap.add_argument("--min-vis", type=float, default=0.5)
    ap.add_argument("--norm-mode", default="auto")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 입력 소스 결정
    if args.manifest:
        src_iter = iter_from_manifest(Path(args.manifest))
    elif args.root:
        src_iter = iter_from_root(Path(args.root))
    else:
        raise SystemExit("ERROR: --manifest 또는 --root 중 하나는 반드시 지정하세요.")

    rows = []
    for video_path, athlete, club in tqdm(src_iter, desc="Analyzing"):
        try:
            res = analyze_one(video_path, club, args.side, args.min_vis, args.norm_mode, args.timeout)
            swing_id = res.get("swingId", "")
            pm = res.get("phase_metrics", {}) or {}
            for phase, metrics in pm.items():
                rows.append({
                    "swing_id": swing_id,
                    "athlete": athlete,
                    "club": club,
                    "video_path": video_path,
                    "phase": phase,
                    "elbow": metrics.get("elbow"),
                    "knee": metrics.get("knee"),
                    "spine_tilt": metrics.get("spine_tilt"),
                    "shoulder_turn": metrics.get("shoulder_turn"),
                    "hip_turn": metrics.get("hip_turn"),
                    "x_factor": metrics.get("x_factor"),
                })
        except Exception as e:
            print(f"[WARN] fail: {video_path} ({athlete}/{club}) -> {e}")

    # CSV 저장
    fieldnames = ["swing_id","athlete","club","video_path","phase",
                  "elbow","knee","spine_tilt","shoulder_turn","hip_turn","x_factor"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"[OK] wrote {len(rows)} rows -> {out}")

if __name__ == "__main__":
    main()