"""Check production configuration before starting the public stack."""

import argparse
import re
import sys
from pathlib import Path

HOST_LABEL = r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
PUBLIC_HOST = re.compile(rf"{HOST_LABEL}(?:\.{HOST_LABEL})*\.[A-Za-z]{{2,63}}")
RESERVED_DOMAINS = (".example", ".invalid", ".localhost", ".test", ".example.com", ".example.net", ".example.org")
RESERVED_BASES = {"example.com", "example.net", "example.org"}


def reserved_host(host: str) -> bool:
    return host.lower() in RESERVED_BASES or host.lower().endswith(RESERVED_DOMAINS)


def values(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if not separator:
                raise ValueError(f"Invalid environment line beginning with {key[:20]!r}")
            result[key] = value.strip().strip('"').strip("'")
    return result


def check(config: dict[str, str]) -> list[str]:
    errors = []
    for key in ("POSTGRES_PASSWORD", "SECRET_KEY", "BFF_SHARED_SECRET"):
        value = config.get(key, "")
        if len(value) < 32 or value.startswith("replace-with"):
            errors.append(f"{key} must be a unique random value of at least 32 characters")
    password = config.get("POSTGRES_PASSWORD", "")
    if password and not re.fullmatch(r"[A-Za-z0-9._~-]+", password):
        errors.append("POSTGRES_PASSWORD must use URL-safe characters")
    secret_values = [config.get(key, "") for key in ("POSTGRES_PASSWORD", "SECRET_KEY", "BFF_SHARED_SECRET")]
    if all(secret_values) and len(set(secret_values)) != 3:
        errors.append("All three secrets must differ")
    domain = config.get("SAHAYA_DOMAIN", "")
    if len(domain) > 253 or not PUBLIC_HOST.fullmatch(domain) or reserved_host(domain):
        errors.append("SAHAYA_DOMAIN must be a real public DNS name")
    email = config.get("TLS_EMAIL", "")
    email_local, _, email_domain = email.rpartition("@")
    if not re.fullmatch(r"[^\s@]+", email_local) or len(email) > 254 or not PUBLIC_HOST.fullmatch(email_domain) or reserved_host(email_domain):
        errors.append("TLS_EMAIL must be a real operator address")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("env_file", type=Path)
    args = parser.parse_args()
    try:
        failures = check(values(args.env_file))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        sys.exit(1)
    print("Production environment values passed static preflight checks")


if __name__ == "__main__":
    main()
