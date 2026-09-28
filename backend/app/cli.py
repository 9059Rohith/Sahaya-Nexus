import argparse
import getpass
import logging
import time
from pathlib import Path

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import User
from .security import hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-admin", "prepare-speech", "worker", "run-maintenance"])
    parser.add_argument("--email")
    parser.add_argument("--name")
    args = parser.parse_args()
    if args.command in {"worker", "run-maintenance"}:
        from .services.maintenance import run_maintenance

        if args.command == "run-maintenance":
            with SessionLocal() as db:
                print(run_maintenance(db))
            return
        logging.basicConfig(level=logging.INFO)
        while True:
            try:
                with SessionLocal() as db:
                    result = run_maintenance(db)
                heartbeat = Path(settings.data_dir) / "worker-heartbeat"
                heartbeat.parent.mkdir(parents=True, exist_ok=True)
                heartbeat.touch()
                if any(result.values()):
                    logging.info("Maintenance: %s", result)
            except Exception:
                logging.exception("Maintenance cycle failed")
            time.sleep(60)
    if args.command == "prepare-speech":
        from faster_whisper import WhisperModel

        WhisperModel(settings.speech_model, device="cpu", compute_type="int8", download_root=f"{settings.data_dir}/models")
        print(f"Local speech model {settings.speech_model} is ready")
        return
    if args.command == "create-admin":
        email = (args.email or input("Email: ")).strip().lower()
        name = (args.name or input("Name: ")).strip()
        password = getpass.getpass("Password (10+ characters): ")
        if len(password) < 10:
            raise SystemExit("Password must be at least 10 characters")
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.email == email)):
                raise SystemExit("User already exists")
            db.add(
                User(
                    email=email,
                    name=name,
                    password_hash=hash_password(password),
                    role="ADMIN",
                    verified=True,
                )
            )
            db.commit()
        print("Admin created")


if __name__ == "__main__":
    main()
