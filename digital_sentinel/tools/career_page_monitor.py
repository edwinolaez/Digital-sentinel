"""
Digital Sentinel — Company Career Page Monitor
Watches a curated list of Calgary/Canadian tech company career pages for changes.
Stores content hashes between runs and reports pages that have been updated,
indicating likely new job postings.
"""
import hashlib
import json
import os
import re
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_SNAPSHOT_PATH = os.path.join(_PROJECT_ROOT, "career_page_snapshots.json")

# ── Target companies ──────────────────────────────────────────────────────────
# Edit this dict to add or remove companies.
TARGET_COMPANIES: dict[str, str] = {
    "Neo Financial":       "https://jobs.lever.co/neofinancial",
    "Bold Commerce":       "https://boldcommerce.com/careers",
    "Benevity":            "https://benevity.com/careers",
    "Symend":              "https://symend.com/careers",
    "Attabotics":          "https://attabotics.com/careers",
    "Miovision":           "https://miovision.com/careers",
    "Helcim":              "https://www.helcim.com/careers",
    "Showpass":            "https://showpass.com/about/careers",
    "Arcurve":             "https://arcurve.com/careers",
    "1Password":           "https://jobs.lever.co/1password",
    "Jobber":              "https://getjobber.com/careers",
    "Trulioo":             "https://www.trulioo.com/company/careers",
}

_JOB_KEYWORDS = re.compile(
    r"\b(developer|engineer|software|frontend|backend|fullstack|full.stack|"
    r"python|react|typescript|javascript|node\.?js|next\.?js|junior|entry.level|"
    r"intern|co.op|new.grad)\b",
    re.IGNORECASE,
)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Digital-Sentinel/1.0; career-page-monitor)"}


# ── Persistence ───────────────────────────────────────────────────────────────

def _load_snapshots() -> dict:
    if os.path.exists(_SNAPSHOT_PATH):
        with open(_SNAPSHOT_PATH) as f:
            return json.load(f)
    return {}


def _save_snapshots(data: dict) -> None:
    with open(_SNAPSHOT_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Page fetching + analysis ──────────────────────────────────────────────────

def _fetch_page_text(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return None


def _extract_snippets(text: str, max_snippets: int = 6) -> list[str]:
    sentences = re.split(r"[.\n|•·]", text)
    snippets = []
    for s in sentences:
        s = s.strip()
        if 20 < len(s) < 150 and _JOB_KEYWORDS.search(s):
            snippets.append(s)
        if len(snippets) >= max_snippets:
            break
    return snippets


# ── Public tool ───────────────────────────────────────────────────────────────

def monitor_career_pages() -> str:
    """Checks target company career pages for changes since the last scan.

    Fetches each company's careers page, hashes the content, and compares
    to the stored snapshot. A changed hash means the page was updated —
    likely new postings were added or removed.

    On the very first run, baselines are saved (no changes reported).
    Run it again after 24 hours to start detecting differences.

    Returns:
        A report listing changed pages (with job-relevant snippets),
        unchanged pages, and any fetch errors.
    """
    snapshots = _load_snapshots()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    changed: list[str] = []
    unchanged: list[str] = []
    errors: list[str] = []

    for company, url in TARGET_COMPANIES.items():
        text = _fetch_page_text(url)
        if text is None:
            errors.append(f"  {company} — could not fetch ({url})")
            continue

        current_hash = hashlib.sha256(text.encode()).hexdigest()
        previous = snapshots.get(company, {})
        prev_hash = previous.get("hash")

        snippets = _extract_snippets(text)
        snippet_block = (
            "\n".join(f"    · {s}" for s in snippets)
            if snippets
            else "    (no tech keywords found)"
        )

        snapshots[company] = {
            "hash": current_hash,
            "last_checked": now,
            "url": url,
        }

        if prev_hash is None:
            unchanged.append(f"  {company} — baseline saved (first scan)")
        elif current_hash != prev_hash:
            changed.append(f"  {company}\n  {url}\n{snippet_block}")
        else:
            unchanged.append(f"  {company} — no change")

    _save_snapshots(snapshots)

    sep = "=" * 46
    report = f"\n{sep}\n CAREER PAGE MONITOR — {now}\n{sep}\n"

    if changed:
        report += f"\nCHANGED ({len(changed)}) — new postings likely:\n"
        for entry in changed:
            report += f"\n{entry}\n"
    else:
        report += "\nNo career page changes detected.\n"

    if unchanged:
        report += f"\nUnchanged ({len(unchanged)}):\n" + "\n".join(unchanged) + "\n"

    if errors:
        report += f"\nFetch errors ({len(errors)}):\n" + "\n".join(errors) + "\n"

    report += f"\n{sep}\n"
    return report


def list_monitored_companies() -> str:
    """Returns the list of companies currently being monitored and their career page URLs.

    Returns:
        Formatted list of company names and URLs.
    """
    lines = [f"  {name}: {url}" for name, url in TARGET_COMPANIES.items()]
    return f"Monitored companies ({len(TARGET_COMPANIES)}):\n" + "\n".join(lines)
