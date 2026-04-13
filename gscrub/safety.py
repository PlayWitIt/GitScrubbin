import subprocess
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BackupInfo:
    branch_name: str
    created_at: datetime
    files_backed_up: List[str]


class Safety:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, text=True, capture_output=True, cwd=self.repo_root)

    def create_backup_branch(self, files: List[str]) -> BackupInfo:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"gscrub-backup-{timestamp}"

        r = self._run(["git", "branch", branch_name])
        if r.returncode != 0:
            raise RuntimeError(f"Failed to create backup branch: {r.stderr}")

        return BackupInfo(
            branch_name=branch_name,
            created_at=datetime.now(),
            files_backed_up=files
        )

    def verify_clean_worktree(self) -> bool:
        r = self._run(["git", "status", "--porcelain"])
        return r.stdout.strip() == ""

    def check_filter_repo_available(self) -> bool:
        r = self._run(["git", "filter-repo", "--version"])
        return r.returncode == 0

    def require_clean_worktree(self) -> None:
        if not self.verify_clean_worktree():
            raise RuntimeError(
                "Dirty worktree detected. Please commit or stash changes before scrubbing."
            )

    def require_filter_repo(self) -> None:
        if not self.check_filter_repo_available():
            raise RuntimeError(
                "git-filter-repo is required but not installed. "
                "Install with: pipx install git-filter-repo"
            )