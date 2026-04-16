import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", ROOT_DIR / "checkpoints"))


def extract_google_drive_id(url: str) -> str | None:
    parsed = urlparse(url)
    if "drive.google.com" not in parsed.netloc:
        return None

    query_id = parse_qs(parsed.query).get("id")
    if query_id:
        return query_id[0]

    parts = [part for part in parsed.path.split("/") if part]
    if "d" in parts:
        index = parts.index("d")
        if index + 1 < len(parts):
            return parts[index + 1]

    return None


def ensure_file_from_env(env_name: str, target_name: str) -> None:
    url = os.getenv(env_name)
    target_path = CHECKPOINT_DIR / target_name

    if target_path.exists():
        print(f"[startup] Found {target_name}, skipping download.")
        return

    if not url:
        print(f"[startup] {target_name} missing and {env_name} is not set.", file=sys.stderr)
        return

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[startup] Downloading {target_name} from {env_name}...")
    file_id = extract_google_drive_id(url)
    if file_id:
        command = [sys.executable, "-m", "gdown", "--id", file_id, "-O", str(target_path)]
    else:
        command = [sys.executable, "-m", "gdown", url, "-O", str(target_path)]

    subprocess.run(command, check=True)


def main() -> None:
    ensure_file_from_env("BEST_MODEL_URL", "best_model.pt")
    ensure_file_from_env("FINAL_MODEL_URL", "final_model.pt")

    port = os.getenv("PORT", "8000")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
