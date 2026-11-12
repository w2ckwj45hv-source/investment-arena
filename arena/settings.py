"""Liest und speichert geheime Schlüssel in der Datei .env im Projektordner."""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _read() -> dict:
    out = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"')
    return out


def get(name: str):
    return os.environ.get(name) or _read().get(name) or None


def set_many(values: dict):
    data = _read()
    data.update({k: v.strip() for k, v in values.items()})
    ENV_FILE.write_text("".join(f"{k}={v}\n" for k, v in data.items()), encoding="utf-8")
    ENV_FILE.chmod(0o600)
