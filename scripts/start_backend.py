import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request


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
        download_google_drive_file(file_id, target_path)
    else:
        raise RuntimeError(f"Unsupported download URL for {env_name}. Use a Google Drive share link.")


def download_google_drive_file(file_id: str, target_path: Path) -> None:
    opener = build_opener(HTTPCookieProcessor())
    base_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    with opener.open(Request(base_url, headers={"User-Agent": "Mozilla/5.0"})) as response:
        html = response.read().decode("utf-8", errors="ignore")

    confirm_token = None
    token_match = re.search(r'name="confirm"\s+value="([^"]+)"', html)
    if token_match:
        confirm_token = token_match.group(1)
    else:
        for marker in ("confirm=", "confirm=t&confirm="):
            if marker in html:
                fragment = html.split(marker, 1)[1]
                confirm_token = fragment.split("&", 1)[0].split('"', 1)[0]
                break

    download_url = base_url if not confirm_token else (
        f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
    )

    with opener.open(Request(download_url, headers={"User-Agent": "Mozilla/5.0"})) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            body = response.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                "Google Drive download failed. Make sure the file is shared as "
                "'Anyone with the link' and that download quota is not exceeded.\n"
                f"Response snippet: {body[:300]}"
            )

        with open(target_path, "wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)


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
