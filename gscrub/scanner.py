import subprocess
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FileTarget:
    path: str
    exists_in_worktree: bool
    exists_in_history: bool
    last_commit_hash: Optional[str] = None
    last_commit_msg: Optional[str] = None
    first_commit_hash: Optional[str] = None
    commit_count: int = 0


class Scanner:
    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, text=True, capture_output=True, cwd=self.repo_root)

    def git_root(self) -> str:
        r = self._run(["git", "rev-parse", "--show-toplevel"])
        if r.returncode != 0:
            raise RuntimeError("Not a git repository")
        return r.stdout.strip()

    def is_ignored(self, path: str) -> bool:
        r = self._run(["git", "check-ignore", "-q", path])
        return r.returncode == 0

    def list_tracked_files(self) -> List[str]:
        r = self._run(["git", "ls-files"])
        return [f for f in r.stdout.splitlines() if f.strip()]

    def list_all_in_history(self) -> List[str]:
        r = self._run([
            "git", "log", "--all", "--pretty=format:",
            "--name-only"
        ])
        files = set()
        for line in r.stdout.splitlines():
            if line.strip() and not line.startswith(" "):
                files.add(line.strip())
        return sorted(files)

    def get_file_info(self, path: str) -> FileTarget:
        worktree_r = self._run(["git", "ls-files", "--error-unmatch", path])
        exists_in_worktree = worktree_r.returncode == 0

        history_r = self._run([
            "git", "log", "--all", "--pretty=format:%H %s",
            "--name-only", "--", path
        ])
        history_lines = [l for l in history_r.stdout.splitlines() if l.strip()]
        exists_in_history = len(history_lines) > 0

        last_hash, last_msg = None, None
        first_hash = None
        count = 0

        if exists_in_history:
            count = len(history_lines)
            first_line = history_lines[0]
            parts = first_line.split(" ", 1)
            first_hash = parts[0] if parts else None
            if len(history_lines) > 1:
                last_line = history_lines[-1]
                parts = last_line.split(" ", 1)
                last_hash = parts[0]
                last_msg = parts[1] if len(parts) > 1 else ""

        return FileTarget(
            path=path,
            exists_in_worktree=exists_in_worktree,
            exists_in_history=exists_in_history,
            last_commit_hash=last_hash,
            last_commit_msg=last_msg,
            first_commit_hash=first_hash,
            commit_count=count
        )

    def scan(self) -> List[FileTarget]:
        all_files = set(self.list_tracked_files()) | set(self.list_all_in_history())

        targets = []
        for path in all_files:
            if self.is_ignored(path):
                continue
            info = self.get_file_info(path)
            if info.exists_in_worktree or info.exists_in_history:
                targets.append(info)

        return targets