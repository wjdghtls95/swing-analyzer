# scripts/bootstrap_dirs.py
from scripts.utils.libs.fs import ensure_dirs, REQUIRED_DIRS


def main():
    ensure_dirs(REQUIRED_DIRS)
    print("[ok] required directories are ready.")


if __name__ == "__main__":
    main()
