import argparse, json, subprocess
from pathlib import Path

def run(cmd):
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)  # queries/pro_swing_videos.json
    ap.add_argument("--out", default="data/videos/pros_faceon")
    ap.add_argument("--yt_dlp", default="yt-dlp")  # 설치: pip install yt-dlp
    args = ap.parse_args()

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)

    data = json.loads(Path(args.queries).read_text())
    for athlete, clubs in data.items():
        for club, urls in clubs.items():
            out_dir = root / athlete / club
            out_dir.mkdir(parents=True, exist_ok=True)
            for url in urls:
                # 파일명 자동(unique) 저장
                cmd = [
                    args.yt_dlp,
                    "--no-check-certificate",
                    "-o", str(out_dir / "%(title)s-%(id)s.%(ext)s"),
                    url
                ]
                run(cmd)

if __name__ == "__main__":
    main()