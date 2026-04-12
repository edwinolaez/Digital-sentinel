"""
Digital Sentinel — Repo Auditor (ADK tool wrapper)
Wraps the standalone RepoAuditor class from safety_auditor.py so it can be
registered as a tool on any LlmAgent.
"""
from ..safety_auditor import RepoAuditor as _RepoAuditor

_auditor: _RepoAuditor | None = None


def _get_auditor() -> _RepoAuditor:
    global _auditor
    if _auditor is None:
        _auditor = _RepoAuditor()
    return _auditor


def audit_github_repo(repo_url: str) -> str:
    """Audits a GitHub repository for security red flags before cloning or forking.

    Checks for archived status, unusually low star count, open issue density,
    and other risk indicators via the GitHub API.

    Args:
        repo_url: Full GitHub URL, e.g. https://github.com/owner/repo-name

    Returns:
        A Sentinel audit report with a SAFE / CAUTION / DANGEROUS verdict.
    """
    return _get_auditor().audit(repo_url)
