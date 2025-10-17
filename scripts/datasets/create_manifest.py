import json
from pathlib import Path
import argparse

def make_manifest(root_dir: str, out_path: str):
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"root_dir not found: {root}")

    items = []
    for pro_dir in sorted(root.iterdir()):
        if not pro_dir.is_dir():
            continue
        pro = pro_dir.name
        for club_dir in sorted(pro_dir.iterdir()):
            if not club_dir.is_dir():
                continue
            club = club_dir.name
            for file in sorted(club_dir.glob("*.mp4")):
                items.append({
                    "pro": pro,
                    "club": club,
                    "path": str(file.resolve())
                })

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    print(f"✅ Manifest created: {out} ({len(items)} items)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Root directory containing pro videos")
    parser.add_argument("--out", required=True, help="Output manifest.json path")
    args = parser.parse_args()
    make_manifest(args.root, args.out)

if __name__ == "__main__":
    main()