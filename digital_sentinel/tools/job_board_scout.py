"""
Digital Sentinel — Job Board Scout
Fetches live software job postings from RemoteOK and Arbeitnow.
Both boards have significantly less applicant volume than LinkedIn/Indeed,
making them much better channels for new graduates.
Every posting is scanned for scam signals before being surfaced.
"""
import re

import requests

from .scam_detector import scan_for_scam_signals

_HEADERS = {"User-Agent": "Digital-Sentinel/1.0 (job-search-tool)"}

_LEVEL_RE = re.compile(
    r"\b(junior|entry.level|entry level|intern|internship|co.op|coop|"
    r"new.grad|new grad|graduate|associate|0.2 years|0 to 2)\b",
    re.IGNORECASE,
)

_TECH_RE = re.compile(
    r"\b(python|react|typescript|javascript|next\.?js|node\.?js|"
    r"fullstack|full.stack|full stack|frontend|front.end|backend|back.end|"
    r"software developer|software engineer|web developer|"
    r"flask|fastapi|django|rest api|sql|mongodb)\b",
    re.IGNORECASE,
)


def _score(text: str) -> str | None:
    has_level = bool(_LEVEL_RE.search(text))
    has_tech = bool(_TECH_RE.search(text))
    if has_level and has_tech:
        return "MATCH"
    if has_tech:
        return "REVIEW"
    return None


def _fetch_remoteok() -> list[dict]:
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return [j for j in resp.json() if isinstance(j, dict) and j.get("position")]
    except Exception as e:
        return [{"_error": f"RemoteOK: {e}"}]


def _fetch_arbeitnow() -> list[dict]:
    try:
        resp = requests.get(
            "https://arbeitnow.com/api/job-board-api",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        return [{"_error": f"Arbeitnow: {e}"}]


def _format_job(source: str, title: str, company: str, tags: str, url: str, scam_risk: str = "CLEAR") -> str:
    risk_tag = "" if scam_risk == "CLEAR" else f"  [!] SCAM RISK: {scam_risk}\n"
    return (
        f"  [{source}] {title}  @  {company}\n"
        f"    Tags : {tags or 'none'}\n"
        f"    URL  : {url}\n"
        f"{risk_tag}"
    ).rstrip()


def fetch_job_board_postings(max_results: int = 40) -> str:
    """Fetches fresh entry-level software job postings from RemoteOK and Arbeitnow.

    Both boards have far less applicant volume than LinkedIn/Indeed and are
    strong channels for remote/hybrid junior roles. Postings are scored against
    Edwin's stack (Python, React, TypeScript, Next.js, Node.js) and tagged
    as MATCH (level + tech match) or REVIEW (tech match only).

    Args:
        max_results: Maximum number of scored postings to return (default 40).

    Returns:
        Scored and labelled job listings grouped by verdict, with source,
        tags, and direct URLs.
    """
    sources = [
        ("RemoteOK", _fetch_remoteok()),
        ("Arbeitnow", _fetch_arbeitnow()),
    ]

    matches: list[str] = []
    reviews: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    count = 0

    for source_name, jobs in sources:
        for job in jobs:
            if "_error" in job:
                errors.append(f"  {job['_error']}")
                continue

            if count >= max_results:
                break

            # Normalise fields across the two APIs
            title = (job.get("position") or job.get("title") or "").strip()
            company = (job.get("company") or job.get("company_name") or "?").strip()
            url = job.get("url") or ""
            raw_tags = job.get("tags") or []
            tags_str = (
                ", ".join(str(t) for t in raw_tags[:6])
                if isinstance(raw_tags, list)
                else str(raw_tags)
            )

            dedup_key = f"{title}|{company}".lower()
            if not title or dedup_key in seen:
                continue
            seen.add(dedup_key)

            verdict = _score(f"{title} {tags_str}")
            if verdict is None:
                continue

            # Scam scan — skip outright SCAM postings, flag CAUTION ones
            scam = scan_for_scam_signals(f"{title} {tags_str}")
            if scam["risk"] == "SCAM":
                continue  # Drop silently from results

            formatted = _format_job(source_name, title, company, tags_str, url, scam["risk"])
            if verdict == "MATCH":
                matches.append(formatted)
            else:
                reviews.append(formatted)

            count += 1

    sep = "=" * 46
    report = f"\n{sep}\n JOB BOARD SCOUT  (RemoteOK + Arbeitnow)\n{sep}\n"

    if matches:
        report += f"\nStrong Matches ({len(matches)}):\n\n" + "\n\n".join(matches) + "\n"

    if reviews:
        # Cap reviews in the report so it stays readable
        shown = reviews[:12]
        report += f"\nWorth Reviewing ({len(reviews)} total, showing {len(shown)}):\n\n"
        report += "\n\n".join(shown) + "\n"

    if not matches and not reviews:
        report += "\nNo matching postings found. Try again later — both boards update frequently.\n"

    if errors:
        report += "\nSource errors:\n" + "\n".join(errors) + "\n"

    report += (
        f"\nSummary: {len(matches)} strong match(es), {len(reviews)} to review "
        f"— sourced from RemoteOK and Arbeitnow.\n"
    )
    report += f"{sep}\n"
    return report
