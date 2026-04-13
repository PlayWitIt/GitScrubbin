import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Set

from gscrub.scanner import FileTarget, Scanner


class RiskLevel(Enum):
    CRITICAL = "critical"  # Definitely secret - must scrub
    HIGH = "high"           # Probably secret - should scrub  
    MEDIUM = "medium"      # Might be sensitive - user decides
    LOW = "low"           # Build artifacts - usually ignore
    SAFE = "safe"         # Not a security concern


# Patterns that DEFINITELY contain secrets
# If these are in history, they're exposed
DEFINITELY_SECRET: Set[str] = {
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_x25519",
}

# File patterns that are PROBABLY secrets
# Could be config files with embedded secrets, or could be templates
PROBABLY_SECRET_EXTENSIONS: Set[str] = {
    ".env",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".pkcs12",
}

# File patterns that MIGHT be sensitive
# Config files, etc - need human judgment
MIGHT_BE_SENSITIVE_NAMES: Set[str] = {
    "credentials",
    "secrets",
    "config",
    "api_key",
    "api-token",
    "access_token",
    "refresh_token",
    "client_secret",
    "aws_credentials",
    "service_account",
}


def categorize_file(path: str) -> RiskLevel:
    """
    Categorize a file based ONLY on its path/filename.
    
    This is a conservative guess - we err on the side of showing
    the user more files and letting them decide.
    """
    path_lower = path.lower()
    filename = path_lower.split("/")[-1]
    
    # CRITICAL: Definitely secret keys
    # SSH private keys, PKCS bundles - these are ALWAYS secret
    if filename.startswith("id_") and (
        filename.endswith(".pub") is False
    ):
        return RiskLevel.CRITICAL
    
    if any(secret in filename for secret in DEFINITELY_SECRET):
        return RiskLevel.CRITICAL
    
    # CRITICAL: Certificate bundles
    if filename.endswith((".p12", ".pfx", ".pkcs12")):
        return RiskLevel.CRITICAL
    
    # HIGH: Probably secret
    # .env files are almost always real envs
    if filename == ".env":
        return RiskLevel.HIGH
    
    # .pem and .key files could be certificates or private keys
    if filename.endswith((".pem", ".key")):
        return RiskLevel.HIGH
    
    # Credentials files
    if "credentials" in filename:
        return RiskLevel.HIGH
    
    # AWS credentials
    if "aws" in filename and "credentials" in filename:
        return RiskLevel.HIGH
    
    # HIGH: Tokens and secrets
    if any(x in filename for x in [
        "token", "secret", "api_key", "apikey",
        "client_secret", "client_secret"
    ]):
        return RiskLevel.HIGH
    
    # MEDIUM: Might be sensitive
    # Config files that could have embedded secrets
    if filename.endswith((".yml", ".yaml", ".json", ".xml", ".toml")):
        if any(x in filename for x in [
            "config", "secrets", "settings", "credentials"
        ]):
            return RiskLevel.MEDIUM
    
    # SQL dumps
    if "dump" in filename or filename.endswith(".sql"):
        return RiskLevel.MEDIUM
    
    # LOW: Build artifacts
    # These aren't security issues, just clutter
    low_patterns = [
        "__pycache__",
        "node_modules",
        "vendor",
        ".cache",
        "tmp",
        "temp",
        ".pyc",
        ".pyo",
        ".so",
        ".dll",
        ".dylib",
        ".egg-info",
        "dist",
        "build",
    ]
    
    for pattern in low_patterns:
        if pattern in path_lower:
            return RiskLevel.LOW
    
    # Default: MEDIUM for anything in history
    # (Better to show too much than too little)
    return RiskLevel.MEDIUM


def get_risk_explanation(path: str, level: RiskLevel) -> str:
    """Explain why a file got its risk level."""
    filename = path.lower().split("/")[-1]
    
    explanations = {
        RiskLevel.CRITICAL: {
            "id_rsa": "SSH private key - gives server access",
            "id_ed25519": "SSH private key - gives server access", 
            "id_dsa": "SSH private key - gives server access",
            ".p12": "Certificate bundle - contains private key",
            ".pfx": "Certificate bundle - contains private key",
        },
        RiskLevel.HIGH: {
            ".env": "Environment file - likely has API keys",
            ".pem": "Certificate or private key",
            ".key": "Private key",
            "credentials": "May contain credentials",
            "api_key": "Contains API key",
            "api-token": "Contains API token",
            "token": "Contains token",
            "secret": "Contains secret",
        },
        RiskLevel.MEDIUM: {
            ".yml": "Config - may have embedded secrets",
            ".yaml": "Config - may have embedded secrets",
            ".json": "Config - may have embedded secrets",
            ".xml": "Config - may have embedded secrets",
            "config": "Config file - may have secrets",
            "secrets": "May contain secrets",
            "settings": "Settings file",
            "dump.sql": "SQL dump - may have data",
            ".py": "Python code - old code in history",
            ".js": "JavaScript code - old code in history",
            ".sh": "Shell script - old code in history",
        },
        RiskLevel.LOW: {
            "node_modules": "Dependencies (not a security risk)",
            "vendor": "Dependencies (not a security risk)",
            "__pycache__": "Python cache (not a security risk)",
            ".pyc": "Compiled Python (not a security risk)",
        },
    }
    
    # Try exact filename first
    if filename in explanations.get(level, {}):
        return explanations[level][filename]
    
    # Try partial match
    for pattern, explanation in explanations.get(level, {}).items():
        if pattern in filename:
            return explanation
    
    # Default message based on level
    defaults = {
        RiskLevel.MEDIUM: "Old code or file in history",
        RiskLevel.LOW: "Build artifact",
        RiskLevel.SAFE: "Safe to keep",
    }
    
    return defaults.get(level, "File in Git history")


@dataclass
class AnalysisResult:
    target: FileTarget
    risk_level: RiskLevel
    explanation: str

    @property
    def is_scrubbable(self) -> bool:
        # Show CRITICAL, HIGH, and MEDIUM by default
        # LOW and SAFE are usually noise
        return self.risk_level in (
            RiskLevel.CRITICAL,
            RiskLevel.HIGH,
            RiskLevel.MEDIUM,
        )


class Analyzer:
    def __init__(self, scanner: Scanner):
        self.scanner = scanner

    def analyze(self, target: FileTarget) -> AnalysisResult:
        level = categorize_file(target.path)
        explanation = get_risk_explanation(target.path, level)
        
        return AnalysisResult(
            target=target,
            risk_level=level,
            explanation=explanation,
        )

    def analyze_all(self, targets: List[FileTarget]) -> List[AnalysisResult]:
        """Analyze all targets and return scrubbable ones."""
        results = [self.analyze(t) for t in targets]
        return [r for r in results if r.is_scrubbable]

    def analyze_all_raw(self, targets: List[FileTarget]) -> List[AnalysisResult]:
        """Analyze all targets including LOW/SAFE for verbose mode."""
        return [self.analyze(t) for t in targets]

    def get_scrubbable(self, targets: List[FileTarget]) -> List[FileTarget]:
        results = self.analyze_all(targets)
        return [r.target for r in results]