import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

from gscrub.scanner import FileTarget, Scanner


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SAFE = "safe"


SENSITIVE_PATTERNS = [
    (r"\.env(?:\.[a-zA-Z0-9_-]+)?$", "env file", 3),
    (r"\.env$", "env file", 5),
    (r"(?:^|/)id_[rd]sa(?:\.pub)?$", "SSH private key", 5),
    (r"(?:^|/)id_ed25519(?:\.pub)?$", "SSH private key", 5),
    (r"(?:^|/)credentials\.json?$", "credentials file", 5),
    (r"(?:^|/)credentials\.xml$", "credentials file", 5),
    (r"(?:^|/)serviceAccountKey\.json$", "GCP key", 5),
    (r"\.pem$", "certificate/key", 3),
    (r"\.key$", "private key", 3),
    (r"\.p12$", "PKCS12 bundle", 5),
    (r"\.pfx$", "PKCS12 bundle", 5),
    (r"(?:^|/)secrets\.ya?ml$", "secrets config", 4),
    (r"(?:^|/)secrets\.json$", "secrets config", 4),
    (r"(?:^|/)config\.ya?ml$", "config file", 1),
    (r"(?:^|/)config\.json$", "config file", 1),
    (r"(?:^|/)aws-credentials$", "AWS credentials", 5),
    (r"(?:^|/)aws\.credentials$", "AWS credentials", 5),
    (r"(?:^|/)credentials$", "credentials file", 3),
    (r"(?:^|/)(?:private|secret)[_-]?key", "private key", 3),
    (r"(?:^|/)token$", "token file", 2),
    (r"(?:^|/)access_token", "access token", 4),
    (r"(?:^|/)refresh_token", "refresh token", 4),
    (r"(?:^|/)api[_-]?key", "API key", 4),
    (r"(?:^|/)api[_-]?token", "API token", 4),
    (r"(?:^|/)client[_-]?secret", "client secret", 5),
    (r"(?:^|/)oauth", "OAuth secret", 4),
    (r"password", "password file", 2),
    (r"secret", "secret file", 2),
    (r"token", "token file", 2),
    (r"\.sqlite3?$", "SQLite DB (may contain data)", 2),
    (r"\.db$", "database file", 2),
    (r"(?:^|/)dump\.sql$", "SQL dump", 3),
    (r"(?:^|/)backup.*\.sql$", "SQL backup", 3),
    (r"(?:^|/).*\.bak$", "backup file", 1),
    (r"(?:^|/)tmp/", "temporary directory", 1),
    (r"(?:^|/)temp/", "temporary directory", 1),
    (r"(?:^|/)cache/", "cache directory", 1),
    (r"\bnode_modules/$", "node_modules", 1),
    (r"\bvendor/$", "vendor directory", 1),
    (r"(?:^|/)__pycache__/$", "Python cache", 1),
    (r"(?:^|/)DS_Store$", "macOS metadata", 1),
    (r"(?:^|/)Thumbs\.db$", "Windows metadata", 1),
]


@dataclass
class AnalysisResult:
    target: FileTarget
    risk_level: RiskLevel
    risk_score: int
    matched_pattern: Optional[str]
    pattern_description: Optional[str]
    reasons: List[str]

    @property
    def is_scrubbable(self) -> bool:
        return self.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM)


class Analyzer:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def analyze(self, target: FileTarget) -> AnalysisResult:
        reasons = []
        score = 0
        matched_pattern = None
        pattern_description = None

        path = target.path.lower()

        for pattern, desc, pts in SENSITIVE_PATTERNS:
            if re.search(pattern, path):
                score += pts
                matched_pattern = pattern
                pattern_description = desc
                reasons.append(f"matches pattern: {desc}")
                break

        if target.exists_in_history:
            score += 2
            reasons.append(f"present in {target.commit_count} commit(s) in history")

        if target.exists_in_worktree:
            reasons.append("currently tracked in worktree")
        else:
            reasons.append("deleted but still in history")
            score += 1

        if not target.exists_in_worktree and not target.exists_in_history:
            return AnalysisResult(
                target=target,
                risk_level=RiskLevel.SAFE,
                risk_score=0,
                matched_pattern=None,
                pattern_description=None,
                reasons=["file no longer exists in repository"]
            )

        if score >= 6:
            level = RiskLevel.CRITICAL
        elif score >= 4:
            level = RiskLevel.HIGH
        elif score >= 2:
            level = RiskLevel.MEDIUM
        elif score >= 1:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.SAFE

        return AnalysisResult(
            target=target,
            risk_level=level,
            risk_score=score,
            matched_pattern=matched_pattern,
            pattern_description=pattern_description,
            reasons=reasons
        )

    def analyze_all(self, targets: List[FileTarget]) -> List[AnalysisResult]:
        results = [self.analyze(t) for t in targets]
        return [r for r in results if r.is_scrubbable]

    def get_scrubbable(self, targets: List[FileTarget]) -> List[FileTarget]:
        results = self.analyze_all(targets)
        return [r.target for r in results if r.is_scrubbable]