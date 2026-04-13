# GitScrubbin — Git Safety Guardian

<p align="center">
  <strong>A safety-first Git "leak prevention system" that detects accidental sensitive file exposures and helps you scrub them safely.</strong>
</p>

---

## Overview

GitScrubbin is your personal Git guardian. It scans your repository for accidentally committed sensitive files (env files, credentials, keys, tokens, secrets) and guides you through safely removing them from Git history.

### Why GitScrubbin?

- **Safety First** — Always creates a backup branch before any changes
- **Guided Experience** — Walks you through the process step-by-step
- **Transparent** — Shows exactly what will be removed and the impact
- **Recoverable** — Nothing is permanent; you can always recover

---

## Installation

### Prerequisites

```bash
# Python 3.9+
python --version

# git-filter-repo (required for history rewriting)
pipx install git-filter-repo
# or: pip install git-filter-repo
```

### Install GitScrubbin

```bash
# From source
pip install -e .

# Or build and install
pip build .
pip install dist/gitscrubbin-*.whl
```

---

## Usage

### Interactive Mode (Recommended)

```bash
gitscrubbin
```

The tool will:
1. Scan your repository for sensitive files
2. Display a table with risk levels
3. Let you select files to scrub via checkbox
4. Show impact analysis
5. Create a backup branch automatically
6. Request explicit "SCRUB" confirmation
7. Rewrite history safely

### Non-Interactive Mode

```bash
# Preview what would be scrubbed (dry run)
gitscrubbin --files .env --dry-run

# Scrub specific files (skip interactive selection)
gitscrubbin --files .env,credentials.json --yes

# Show all files (not just scrubbable)
gitscrubbin --verbose
```

---

## Command Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--files` | `-f` | Comma-separated list of files to scrub |
| `--verbose` | `-v` | Show all files, not just scrubbable ones |
| `--dry-run` | `-n` | Preview only, don't actually scrub |
| `--yes` | `-y` | Skip confirmation prompt |

---

## Risk Levels

| Level | Description |
|-------|-------------|
| **CRITICAL** | Private keys, credentials, tokens, secrets |
| **HIGH** | Env files, AWS credentials, OAuth secrets |
| **MEDIUM** | Config files, SQL dumps, backups |
| **LOW** | Temporary files, cache directories |
| **SAFE** | Files that don't pose exposure risk |

---

## Safety Features

- **Backup Branch** — Automatically creates `gscrubbin-backup-TIMESTAMP` branch before any changes
- **Clean Worktree Required** — Won't run with uncommitted changes
- **Dry Run Support** — Preview impact before executing
- **Explicit Confirmation** — Requires typing "SCRUB" to proceed
- **Impact Analysis** — Shows exactly how many commits will be affected

---

## Detection Patterns

GitScrubbin automatically detects:

- Environment files (`.env`, `.env.*`)
- SSH keys (`id_rsa`, `id_ed25519`, `*.pem`, `*.key`)
- Credentials files (`credentials.json`, `credentials.xml`, `aws-credentials`)
- API keys and tokens (`api_key`, `access_token`, `refresh_token`)
- OAuth secrets (`client_secret`, `oauth`)
- Databases (`*.sqlite`, `*.db`, `dump.sql`)
- Backups and temp files (`*.bak`, `tmp/`, `temp/`, `cache/`)

---

## Example

```bash
$ gitscrubbin

╭────────────────────────────────────────────────────────╮
│ GitScrubbin — Git Safety Guardian                       │
│ Detect accidental exposures. Scrub safely. No regrets.╰────────────────────────────────────────────────────────╯

Scanning repository...

  Found 3 potential targets
Analyzing risk...

                    Scrubbable Targets                     
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ File            ┃ Risk    ┃ Status          ┃ History ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━┇━━━━━━━━━┩
│ .env            │ HIGH    │ tracked        │ 2 commits│
│ credentials.json│ CRITICAL│ tracked        │ 1 commits│
│ config.yml      │ MEDIUM  │ deleted        │ 3 commits│
└─────────────────┴─────────┴────────────────┴─────────┘

? Select files to scrub (space to toggle, enter when done):
[*] .env
[*] credentials.json
[ ] config.yml

Files selected: 2
Commits affected: 3
⚠ This will rewrite Git history!

Backup branch: gscrubbin-backup-20240115-143022

? Type SCRUB to confirm: SCRUB

🧼 Scrubbing...

  1. .env
  2. credentials.json

✅ Scrub complete!

Next Steps

Force push to update remote:
  git push --force --all
  git push --force --tags

Recovery: git checkout gscrubbin-backup-20240115-143022
```

---

## Troubleshooting

### "git-filter-repo is required but not installed"

```bash
pipx install git-filter-repo
```

### "Dirty worktree detected"

Commit or stash your changes before running GitScrubbin:

```bash
git add .
git commit -m "WIP"
```

### Need to recover?

```bash
# List backup branches
git branch | grep gscrubbin-backup

# Switch to backup
git checkout gscrubbin-backup-TIMESTAMP
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check gscrub/

# Type check
mypy gscrub/
```

---

## License

MIT — PlayWit Creations

---

## Related

- [git-filter-repo](https://github.com/newren/git-filter-repo) — The engine that powers history rewriting
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) — Java-based alternative