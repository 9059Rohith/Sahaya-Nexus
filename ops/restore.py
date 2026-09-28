"""Verify a backup, or explicitly replace a stopped production installation."""

import argparse
import hashlib
import json
import posixpath
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent


def verify(directory: Path) -> None:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name in ("database.dump", "evidence.tar.gz"):
        path = directory / name
        expected = manifest["files"][name]
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        if path.stat().st_size != expected["bytes"] or checksum.hexdigest() != expected["sha256"]:
            raise ValueError(f"Backup integrity check failed: {name}")
    with (directory / "database.dump").open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise ValueError("Database file is not a PostgreSQL custom archive")
    with tarfile.open(directory / "evidence.tar.gz", "r:gz") as archive:
        for member in archive:
            if not (member.isfile() or member.isdir() or member.issym()):
                raise ValueError("Evidence archive contains an unsupported member type")
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Evidence archive contains an unsafe path")
            if member.issym():
                destination = posixpath.normpath(posixpath.join(posixpath.dirname(member.name), member.linkname))
                if posixpath.isabs(member.linkname) or destination == ".." or destination.startswith("../"):
                    raise ValueError("Evidence archive contains an unsafe symlink")


def compose_command(env_file: Path, compose_file: Path, *args: str, input_file: Path | None = None, silent: bool = False) -> None:
    command = ["docker", "compose", "--env-file", str(env_file), "-f", str(compose_file), *args]
    if input_file:
        with input_file.open("rb") as stream:
            subprocess.run(command, cwd=ROOT, stdin=stream, stdout=subprocess.DEVNULL if silent else None, check=True)
    else:
        subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.production")
    parser.add_argument("--compose-file", type=Path, default=ROOT / "compose.production.yaml")
    parser.add_argument("--confirm-replace", action="store_true", help="Delete and replace the current database and private files")
    args = parser.parse_args()
    directory = args.backup.resolve()
    verify(directory)
    print(f"Backup integrity verified: {directory}")
    if not args.confirm_replace:
        return
    if not args.env_file.is_file() or not args.compose_file.is_file():
        parser.error("The environment and Compose files must exist for restore")
    env_file = args.env_file.resolve()
    compose_file = args.compose_file.resolve()

    def run(*command: str, input_file: Path | None = None, silent: bool = False) -> None:
        compose_command(env_file, compose_file, *command, input_file=input_file, silent=silent)

    try:
        run("exec", "-T", "db", "pg_restore", "--list", input_file=directory / "database.dump", silent=True)
        run("stop", "ingress", "web", "worker", "api")
        run("exec", "-T", "db", "dropdb", "-U", "sahaya", "--if-exists", "sahaya")
        run("exec", "-T", "db", "createdb", "-U", "sahaya", "sahaya")
        run("exec", "-T", "db", "pg_restore", "-U", "sahaya", "-d", "sahaya", "--no-owner", input_file=directory / "database.dump")
        code = (
            "import pathlib,shutil,sys,tarfile\n"
            "root=pathlib.Path('/app/data')\n"
            "for item in root.iterdir():\n"
            " shutil.rmtree(item) if item.is_dir() else item.unlink()\n"
            "with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as archive:\n"
            " archive.extractall(root,filter='data')"
        )
        run("run", "--rm", "-T", "--no-deps", "--entrypoint", "python", "api", "-c", code, input_file=directory / "evidence.tar.gz")
        run("up", "-d")
    except subprocess.CalledProcessError:
        print("Restore failed. The application remains stopped; repair or repeat the restore before starting it.", file=sys.stderr)
        raise
    print("Restore completed. Check service health, migration head and access to private evidence.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        sys.exit(1)
