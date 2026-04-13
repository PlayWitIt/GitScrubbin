# BigPickle Development Log

## Project: GitScrubbin — Git Safety Guardian

**Created:** 2024-04-13  
**Author:** PlayWit Creations  
**Purpose:** Safety-first Git "leak prevention system" for detecting and removing accidentally committed sensitive files

---

## Phase 1: Initial Assessment

### What Existed
- Single file `gscrub.py` (~220 lines)
- Basic risk scoring with simple patterns
- Interactive file selection
- Backup branch creation
- Uses `git filter-repo` for history rewriting

### Issues Identified
1. Flat architecture (no separation of concerns)
2. No detection of deleted files still in history
3. Limited sensitivity patterns
4. No impact analysis before execution
5. No error handling or recovery
6. No tests

---

## Phase 2: Architecture Redesign

### Module Structure Created

```
gscrub/
├── __init__.py      # Package exports
├── scanner.py       # Git file discovery
├── analyzer.py    # Risk analysis engine
├── scrubber.py    # History rewriting
├── safety.py      # Backup & safety checks
└── cli.py         # CLI interface
```

### Key Design Decisions

1. **Scanner** — Separated git operations from business logic
   - `list_tracked_files()` — Current worktree
   - `list_all_in_history()` — All files ever committed
   - `get_file_info()` — Per-file metadata (commit count, last commit, etc.)
   - Filters out ignored files automatically

2. **Analyzer** — Risk scoring engine
   - 35+ regex patterns for sensitive files
   - Scoring: CRITICAL(6+), HIGH(4+), MEDIUM(2+), LOW(1+), SAFE(0)
   - Shows reasons for each risk level
   - Identifies deleted files in history

3. **Safety** — Pre-scrub safety checks
   - Creates backup branch with timestamp
   - Verifies clean worktree
   - Checks for git-filter-repo installation

4. **Scrubber** — History rewriting
   - Uses `git filter-repo --path X --invert-paths`
   - Runs per-file (not batch, to handle failures gracefully)
   - Provides impact estimation

5. **CLI** — User interface
   - Click-based (switched from Typer — see issues below)
   - Rich tables for output
   - Non-interactive mode for CI/CD

---

## Phase 3: Issues Encountered &Solutions

### Issue 1: Typer Option Parsing Broken

**Problem:** Typer 0.24.1 with `Annotated` type hints wouldn't parse `--files .env` option correctly. Received empty string regardless of how options were defined.

**Attempts:**
- `files: list[str] = typer.Option(...)` — Failed (TypeError)
- `files: Annotated[str, typer.Option(...)] = ""` — Empty received
- Different option syntaxes — All failed

**Solution:** Switched from Typer to Click. Click's option parsing worked immediately:
```python
@click.option("-f", "--files", default="", help="Files to scrub")
def main(verbose, dry_run, yes, files):
```

### Issue 2: Scanner Missing Deleted Files

**Problem:** Original scanner only checked `git ls-files` (current worktree), missed files deleted but still in history.

**Solution:** Added `list_all_in_history()` method:
```python
def list_all_in_history(self) -> List[str]:
    r = self._run(["git", "log", "--all", "--pretty=format:", "--name-only"])
    # Collects all files from all commits
```

### Issue 3: Regex Pattern Ordering

**Problem:** Some patterns overlap (e.g., `.env` vs `.env.local`).

**Solution:** Analyzer sorts patterns by priority (score) and breaks on first match to avoid double-counting.

### Issue 4: Missing Backup Branch Files

**Problem:** Backup branch should include list of files being scrubbed.

**Solution:** Safety.create_backup_branch() now accepts file list and stores in `BackupInfo.files_backed_up`.

---

## Phase 4: Documentation

### README.md Created
- Installation instructions
- Usage examples (interactive + non-interactive)
- Command reference table
- Risk level explanations
- Troubleshooting section

### pyproject.toml
- Package name: `gitscrubbin`
- Author: PlayWit Creations
- Dependencies: click, rich
- Entry point: `gitscrubbin = gscrub.cli:main`

---

## Phase 5: Testing

### Manual Tests Performed
1. Created test repo with `.env` file committed
2. Scanner correctly identified `.env` as HIGH risk
3. `get_file_info()` returned correct commit count
4. CLI `--files .env --dry-run -y` worked correctly
5. Backup branch created successfully
6. Verbose mode showed all files

### Test Results
```
$ gitscrubbin --files .env --dry-run -y
  Found .env: HIGH (score=5)
  - matches pattern: env file
  - present in 2 commit(s) in history
  - currently tracked in worktree
```

---

## Next Steps

### High Priority
1. **Add tests** — pytest coverage for scanner, analyzer, safety modules
2. **Interactive mode** — Add back questionary for terminal selection
3. **Auto-select critical** — When `--files` not provided, auto-scrub CRITICAL files with `-y`

### Medium Priority
4. **Git hooks integration** — Pre-commit check
5. **Config file** — `~/.gitscrubbin.yaml` for custom patterns
6. **Report JSON output** — `--json` for CI/CD integration

### Future Ideas
7. **Filter patterns** — Custom ignore patterns
8. **Server mode** — GitHub App / GitLab integration
9. **Incremental scrub** — Don't rewrite full history for new files

---

## Commands Reference

```bash
# Install
pip install -e .

# Run
gitscrubbin --help
gitscrubbin -v              # Verbose
gitscrubbin -f .env        # Specific file
gitscrubbin -f .env -n     # Dry run
gitscrubbin -f .env -y     # Auto-confirm
```

---

## Lessons Learned

1. **Click > Typer** for CLI options — more predictable
2. **Separation of concerns** — Easier to test and maintain
3. **Rich output** — Makes CLI much more usable
4. **Safety first** — Always backup before destructive ops

---

*End of BigPickle log*