import subprocess
import time
from dataclasses import dataclass
from typing import List, Callable, Optional

from gscrub.scanner import FileTarget
from gscrub.safety import Safety


@dataclass
class ScrubResult:
    target: FileTarget
    success: bool
    error: Optional[str] = None


class Scrubber:
    def __init__(self, repo_root: str, safety: Safety):
        self.repo_root = repo_root
        self.safety = safety

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, text=True, capture_output=True, cwd=self.repo_root)

    def _get_total_commits_affected(self, files: List[str]) -> int:
        if not files:
            return 0
        
        r = self._run([
            "git", "log", "--all", "--oneline"
        ] + [f"--follow", "--", files[0]] if files else [])
        
        if r.returncode != 0:
            return 0
        
        return len([l for l in r.stdout.splitlines() if l.strip()])

    def dry_run(self, files: List[str]) -> dict:
        r = self._run([
            "git", "filter-repo",
            "--dry-run",
            "--quiet",
            "--paths-requiring-blob-free-conversion"
        ] + files)
        
        return {
            "files": files,
            "estimated_commits": self._get_total_commits_affected(files),
            "warning": r.stdout + r.stderr
        }

    def scrub(
        self, 
        files: List[FileTarget],
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[ScrubResult]:
        paths = [t.path for t in files]
        
        self.safety.require_clean_worktree()
        self.safety.require_filter_repo()
        
        results = []
        
        for i, target in enumerate(files):
            path = target.path
            if progress_callback:
                progress_callback(f"Processing: {path}", i + 1)
            
            r = self._run([
                "git", "filter-repo",
                "--path", path,
                "--invert-paths",
                "--quiet"
            ])
            
            if r.returncode != 0:
                results.append(ScrubResult(
                    target=target,
                    success=False,
                    error=r.stderr
                ))
            else:
                results.append(ScrubResult(
                    target=target,
                    success=True
                ))
            
            time.sleep(0.1)
        
        return results

    def estimate_impact(self, files: List[FileTarget]) -> dict:
        total_commits = sum(t.commit_count for t in files)
        
        return {
            "files_to_remove": len(files),
            "total_commits_affected": total_commits,
            "warning": "This will rewrite Git history. All commits containing these files will be modified."
        }