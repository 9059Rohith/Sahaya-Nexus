"""Take a consistent, offline Compose backup of Postgres and private files."""

import argparse
import hashlib
import json
import subprocess
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(compose: list[str], *args: str, output: Path | None = None) -> None:
    with output.open("wb") if output else nullcontext() as stream:
        subprocess.run([*compose, *args], cwd=ROOT, stdout=stream if output else None, check=True)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.production")
    parser.add_argument("--compose-file", type=Path, default=ROOT / "compose.production.yaml")
    parser.add_argument("--output", type=Path, required=True, help="Existing, private backup parent directory")
    args = parser.parse_args()
    if not args.env_file.is_file() or not args.compose_file.is_file() or not args.output.is_dir():
        parser.error("The environment file, Compose file and backup parent directory must already exist")
    moment = datetime.now(timezone.utc)
    destination = args.output.resolve() / f"sahaya-{moment.strftime('%Y%m%dT%H%M%SZ')}"
    destination.mkdir(mode=0o700)
    compose = ["docker", "compose", "--env-file", str(args.env_file.resolve()), "-f", str(args.compose_file.resolve())]
    stopped = True
    try:
        run(compose, "stop", "web", "worker", "api")
        run(compose, "exec", "-T", "db", "pg_dump", "-U", "sahaya", "-d", "sahaya", "-Fc", output=destination / "database.dump")
        code = "import sys,tarfile\nwith tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:\n archive.add('/app/data', arcname='.')"
        run(compose, "run", "--rm", "-T", "--no-deps", "--entrypoint", "python", "api", "-c", code, output=destination / "evidence.tar.gz")
        files = {name: {"sha256": digest(destination / name), "bytes": (destination / name).stat().st_size} for name in ("database.dump", "evidence.tar.gz")}
        (destination / "manifest.json").write_text(json.dumps({"created_at": moment.isoformat(), "files": files}, indent=2) + "\n", encoding="utf-8")
        print(f"Backup complete: {destination}")
    finally:
        if stopped:
            run(compose, "up", "-d")


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        sys.exit(1)
