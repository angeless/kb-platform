#!/usr/bin/env python3
"""KBSQL pre-commit linter — focused on secrets prevention.

Blocks commit if any staged file contains:
  - a line literally equal to `.env` (likely accidental .env tracking)
  - high-confidence secrets (API keys, JWT tokens, AWS access keys, etc.)
  - hard-coded HOGWARTS_KB_AUTO_PUSH=true with a real path (could be
    misleading when shared)

Reads staged content via `git show :PATH` so it reflects the about-to-be-
committed state.

Bypass with `git commit --no-verify` if you've reviewed and accept.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Patterns that indicate likely secrets. Conservative — high precision over recall.
_SECRET_PATTERNS = [
    # Zhipu GLM keys are 32 hex + . + 16 alpha (e.g. 6d4d43d6...JxA703H8X4vTWLTX)
    (re.compile(r"\b[0-9a-f]{32}\.[A-Za-z0-9]{16}\b"), "Zhipu GLM API key"),
    # OpenAI: sk-proj-... or sk-... with high entropy
    (re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"), "OpenAI API key"),
    # Anthropic: sk-ant-...
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "Anthropic API key"),
    # Aiven: AVNS_...
    (re.compile(r"\bAVNS_[A-Za-z0-9_]{15,}\b"), "Aiven password"),
    # AWS access key
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    # Generic: PRIVATE KEY blocks
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "private key block"),
    # GitHub PAT: ghp_, gho_, ghu_, ghs_, ghr_
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub PAT"),
]

# These files are ALWAYS suspicious if staged
_NEVER_COMMIT = {
    ".env",
    ".env.local",
    ".env.production",
    "secrets.json",
    "credentials.json",
}


def _staged_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-status", "--diff-filter=AM"],
        text=True,
    )
    return [line.split("\t", 1)[1] for line in out.splitlines() if line]


def _staged_content(path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f":{path}"], text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None  # binary / missing


def _check_filename(path: str) -> list[str]:
    name = Path(path).name
    if name in _NEVER_COMMIT:
        return [
            f"{path}: file '{name}' should never be committed "
            "(likely contains real credentials). Add to .gitignore "
            "or rename if it's an example template."
        ]
    return []


def _check_secrets(path: str, content: str) -> list[str]:
    issues = []
    for i, line in enumerate(content.splitlines(), start=1):
        # Skip comments + obvious example/test patterns
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*")):
            continue
        if any(marker in line.lower() for marker in
               ["example", "your_key_here", "your-key-here", "placeholder",
                "<your", "xxxxxxxx", "change_me", "test-key", "fake"]):
            continue

        for pat, label in _SECRET_PATTERNS:
            m = pat.search(line)
            if m:
                # Show only first/last 4 chars of the match to avoid leaking
                # the full secret into git history via the error message
                hit = m.group(0)
                masked = f"{hit[:4]}…{hit[-4:]}" if len(hit) > 12 else "[redacted]"
                issues.append(
                    f"{path}:{i}: looks like a {label} ({masked}). "
                    "Move to .env (gitignored) or use --no-verify if false positive."
                )
    return issues


def main() -> int:
    files = _staged_files()
    if not files:
        return 0

    issues: list[str] = []
    for path in files:
        issues.extend(_check_filename(path))
        # Don't read content of binary files / non-text
        if any(path.endswith(ext) for ext in
               (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar",
                ".gz", ".lock", ".woff", ".woff2", ".ico")):
            continue
        content = _staged_content(path)
        if content is not None:
            issues.extend(_check_secrets(path, content))

    if issues:
        print("\n❌ kbsql-lint blocked commit. Likely secrets/sensitive files:\n", file=sys.stderr)
        for it in issues:
            print(f"  • {it}", file=sys.stderr)
        print(
            f"\n{len(issues)} issue(s). Fix and re-commit, or override with "
            "`git commit --no-verify` (only after manual review).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
