"""
Digital Sentinel — Resume Tools
Fetches and cleans a job posting URL so the resume_coach agent can analyze it.
Runs URL safety and scam content checks before returning any content.
"""
import re

import requests

from .scam_detector import check_url_safety, scan_for_scam_signals, format_safety_report

_HEADERS = {"User-Agent": "Mozilla/5.0 (Digital-Sentinel/1.0; resume-coach)"}

# Tags whose entire content we throw away (scripts, styles, nav, footer, etc.)
_DROP_TAGS = re.compile(
    r"<(script|style|nav|header|footer|aside|noscript)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAGS = re.compile(r"<[^>]+>")
_MULTI_BLANK = re.compile(r"\n{3,}")


def _clean_html(raw: str) -> str:
    text = _DROP_TAGS.sub("", raw)
    text = _HTML_TAGS.sub(" ", text)
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#39;", "'")
            .replace("&quot;", '"')
    )
    lines = [l.strip() for l in text.splitlines()]
    text = "\n".join(l for l in lines if l)
    text = _MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def fetch_job_posting(url: str) -> str:
    """Fetches a job posting URL and returns clean plain text for analysis.

    Runs a URL safety check and scam content scan before returning content.
    If the URL is flagged as SUSPICIOUS or the content as SCAM, a warning
    is prepended so the resume_coach and the user are informed.

    Args:
        url: Full URL of the job posting page.

    Returns:
        Safety report header + clean plain-text content of the job posting,
        truncated to 6000 characters. If the URL is SUSPICIOUS, the fetch
        is blocked and only the warning is returned.
    """
    # ── Step 1: URL safety check ──────────────────────────────────────────────
    url_result = check_url_safety(url)

    if url_result["risk"] == "SUSPICIOUS":
        reasons = "\n".join(f"  ! {r}" for r in url_result["reasons"])
        return (
            f"[SECURITY BLOCK] This URL was flagged as SUSPICIOUS and was not fetched.\n"
            f"Reasons:\n{reasons}\n\n"
            f"Do not visit this link manually either. If you believe this is a legitimate "
            f"posting, paste the job description text directly instead of the URL."
        )

    # ── Step 2: Fetch the page ────────────────────────────────────────────────
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        text = _clean_html(resp.text)
    except requests.exceptions.HTTPError as e:
        return f"[ResumeCoach] HTTP {e.response.status_code} error fetching posting — {url}"
    except Exception as e:
        return (
            f"[ResumeCoach] Could not fetch posting: {e}\n"
            f"Tip: paste the job description text directly instead of the URL."
        )

    # ── Step 3: Scam content scan ─────────────────────────────────────────────
    scam_result = scan_for_scam_signals(text)
    safety_header = format_safety_report(url_result, scam_result)

    warning = ""
    if scam_result["risk"] == "SCAM":
        warning = (
            "\n[!] SCAM WARNING: This posting contains strong fraud indicators. "
            "Do not apply, provide personal information, or click any links in it.\n"
        )
    elif scam_result["risk"] == "CAUTION":
        warning = (
            "\n[~] CAUTION: This posting has some soft scam signals. "
            "Verify the company is real before applying (check LinkedIn, their website, Glassdoor).\n"
        )

    # ── Step 4: Return content with safety header prepended ───────────────────
    if len(text) > 6000:
        text = text[:6000] + "\n\n[... truncated ...]"

    return (
        f"=== SECURITY PRE-CHECK ===\n{safety_header}{warning}\n"
        f"=== JOB POSTING CONTENT ===\n{text}"
    )
