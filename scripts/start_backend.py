import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", ROOT_DIR / "checkpoints"))


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
    subprocess.run(
        [sys.executable, "-m", "gdown", "--fuzzy", url, "-O", str(target_path)],
        check=True,
    )


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
