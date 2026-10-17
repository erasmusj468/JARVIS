"""Download the compact English Vosk model used for offline wake-word listening."""

from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
import shutil
import sys

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_DIR = MODELS / MODEL_NAME
ARCHIVE = MODELS / f"{MODEL_NAME}.zip"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"


def main():
    if MODEL_DIR.is_dir():
        print(f"Voice model is already installed: {MODEL_DIR}")
        return
    MODELS.mkdir(exist_ok=True)
    try:
        print("Downloading the official Vosk English model (about 40 MB)…")
        with urlopen(MODEL_URL, timeout=60) as response, ARCHIVE.open("wb") as output:
            shutil.copyfileobj(response, output)
        print("Extracting model…")
        with ZipFile(ARCHIVE) as archive:
            base = MODELS.resolve()
            for entry in archive.infolist():
                destination = (MODELS / entry.filename).resolve()
                if base not in destination.parents and destination != base:
                    raise ValueError("The model archive contains an unsafe path.")
            archive.extractall(MODELS)
        if not MODEL_DIR.is_dir():
            raise FileNotFoundError(f"Expected model folder was not extracted: {MODEL_DIR}")
        print("Offline speech model is ready. Start JARVIS with: py run.py")
    except Exception as exc:
        print(f"Model setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        ARCHIVE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
