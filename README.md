# gscrub — Git Safety Guardian

<p align="center">
  <strong>A safety-first Git "leak prevention system" that detects accidental sensitive file exposures and helps you scrub them safely.</strong>
</p>

---

## Overview

gscrub is your personal Git guardian. It scans your repository for accidentally committed sensitive files (env files, credentials, keys, tokens, secrets) and guides you through safely removing them from Git history.

### Why gscrub?

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

### Install gscrub

```bash
# From source
pip install -e .

# Or from PyPI (when published)
pip install gscrub

# Or build and install
pip build .
pip install dist/gscrub-*.whl
```

---

## Usage

### Scan Your Repository

```bash
gscrub
```

This will:
1. Scan all files ever committed to your repo (including deleted files)
2. Categorize them by risk level
3. Show you what's in your Git history

### Common Commands

```bash
gscrub              # Scan and show risky files
gscrub -h           # Show help
gscrub -v           # Verbose (show all files, not just risky)
gscrub -f .env      # Scrub specific file(s)
gscrub -n           # Dry run (preview only)
gscrub -y           # Auto-confirm (skip confirmation)
```

---

## Understanding Risk Levels

| Level | What it means | Examples |
|-------|--------------|----------|
| CRITICAL | Definitely secret - MUST scrub | SSH keys, `.p12`, `.pfx` |
| HIGH | Probably secret - SHOULD scrub | `.env`, credentials, tokens |
| MEDIUM | Might be sensitive - you decide | config files, old code |
| LOW | Not a security risk | node_modules, cache |

### Understanding Status

| Status | What it means |
|--------|--------------|
| tracked | File currently exists in your working directory |
| deleted | Was committed, now removed - BUT still in Git history! |

---

## Example Workflow

```bash
# 1. See what files are in your history
$ gscrub

# 2. Preview what will happen (dry run)
$ gscrub -f .env -n

# 3. Actually scrub (creates backup branch first)
$ gscrub -f .env -y

# 4. Force push to remote
$ git push --force --all
$ git push --force --tags

# 5. If something goes wrong, recover
$ git checkout gscrub-backup-20240115-143022
```

---

## Safety Features

- **Backup Branch** — Automatically creates `gscrub-backup-TIMESTAMP` before any changes
- **Dry Run** — Preview with `-n` before actual scrub
- **Impact Analysis** — Shows exactly how many commits will be affected
- **Recovery** — Switch to backup branch to undo

---

## Troubleshooting

### "git-filter-repo is required but not installed"

```bash
pipx install git-filter-repo
```

### "Dirty worktree detected"

Commit or stash your changes first:

```bash
git add .
git commit -m "WIP"
```

### Need to recover?

```bash
# List backup branches
git branch | grep gscrub-backup

# Switch to backup
git checkout gscrub-backup-TIMESTAMP
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