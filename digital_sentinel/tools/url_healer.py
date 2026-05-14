"""
Digital Sentinel — URL Healer
When career_page_monitor detects broken URLs (404s, timeouts, wrong pages),
this tool probes common career page URL patterns to find the real working URL,
then saves the correction to career_url_overrides.json so the next scan uses it.
No source-code edits needed — overrides are applied at runtime.
"""
import json
import os
import re

import requests

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_OVERRIDES_PATH = os.path.join(_PROJECT_ROOT, "career_url_overrides.json")
_SNAPSHOT_PATH = os.path.join(_PROJECT_ROOT, "career_page_snapshots.json")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Digital-Sentinel/1.0; url-healer)"}

# Common career page path suffixes to try, in priority order
_CAREER_SUFFIXES = [
    "/careers",
    "/jobs",
    "/about/careers",
    "/company/careers",
    "/en/careers",
    "/en/jobs",
    "/join-us",
    "/join",
    "/work-with-us",
    "/opportunities",
    "/open-roles",
    "/hiring",
    "/about/jobs",
    "/careers/open-positions",
    "/about/work-here",
]

# Third-party job board URL templates — slug is company name lowercased, no spaces/symbols
_JOB_BOARD_TEMPLATES = [
    "https://jobs.lever.co/{slug}",
    "https://boards.greenhouse.io/{slug}",
    "https://apply.workable.com/{slug}",
    "https://careers.smartrecruiters.com/{slug}",
    "https://{slug}.breezy.hr",
    "https://{slug}.recruitee.com",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slug(company_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", company_name.lower())


def _is_live(url: str) -> bool:
    try:
        resp = requests.head(url, headers=_HEADERS, timeout=10, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False


def _load_overrides() -> dict:
    if os.path.exists(_OVERRIDES_PATH):
        with open(_OVERRIDES_PATH) as f:
            return json.load(f)
    return {}


def _save_overrides(data: dict) -> None:
    with open(_OVERRIDES_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public tools ──────────────────────────────────────────────────────────────

def get_broken_career_urls() -> str:
    """Reads the latest career page snapshot to find all URLs that failed to load.

    The career page monitor saves error details whenever a fetch fails.
    Call this to get the list of companies that need URL healing before running
    find_career_page() on each one.

    Returns:
        A formatted list of company names, broken URLs, and error reasons.
        Returns a clean message if no errors exist.
    """
    if not os.path.exists(_SNAPSHOT_PATH):
        return (
            "No snapshot file found. Run monitor_career_pages() first to create "
            "a baseline and populate the error list."
        )

    with open(_SNAPSHOT_PATH) as f:
        snapshots = json.load(f)

    broken = [
        (company, data.get("url", "?"), data.get("error", "unknown error"))
        for company, data in snapshots.items()
        if "error" in data
    ]

    if not broken:
        return "No broken URLs in the latest snapshot — all career pages loaded successfully."

    lines = [
        f"  {company}\n    URL  : {url}\n    Error: {err}"
        for company, url, err in broken
    ]
    return (
        f"Broken career page URLs ({len(broken)}) — ready for healing:\n\n"
        + "\n\n".join(lines)
    )


def find_career_page(company_name: str, broken_url: str) -> str:
    """Probes common career page URL patterns to find a working URL for a company.

    Strategy:
    1. Extracts the root domain from broken_url.
    2. Tries every suffix in _CAREER_SUFFIXES (/careers, /jobs, /about/careers, …).
    3. If none work, tries third-party job boards (Lever, Greenhouse, Workable, …)
       using the company name as the slug.
    All probes use HEAD requests — no full page downloads.

    Args:
        company_name: Company name exactly as it appears in the monitor list
                      (e.g. 'StellarAlgo').
        broken_url:   The current non-working URL (used to extract the domain).

    Returns:
        The first working URL found, with instructions to save it.
        If nothing works, suggests a manual search and lists what was tried.
    """
    domain_match = re.match(r"(https?://[^/]+)", broken_url)
    if not domain_match:
        return f"[URL Healer] Could not parse a domain from: {broken_url}"

    domain = domain_match.group(1).rstrip("/")
    slug = _slug(company_name)
    tried: list[str] = []

    # Pass 1 — domain + common suffixes
    for suffix in _CAREER_SUFFIXES:
        candidate = domain + suffix
        tried.append(candidate)
        if _is_live(candidate):
            return (
                f"[URL Healer] Working URL found for '{company_name}':\n"
                f"  {candidate}\n\n"
                f"Save it by calling:\n"
                f"  update_career_page_url('{company_name}', '{candidate}')"
            )

    # Pass 2 — third-party job boards
    for template in _JOB_BOARD_TEMPLATES:
        candidate = template.format(slug=slug)
        tried.append(candidate)
        if _is_live(candidate):
            return (
                f"[URL Healer] Found '{company_name}' on a job board:\n"
                f"  {candidate}\n\n"
                f"Save it by calling:\n"
                f"  update_career_page_url('{company_name}', '{candidate}')"
            )

    return (
        f"[URL Healer] No working career page found for '{company_name}' "
        f"after trying {len(tried)} URLs.\n"
        f"The site may require JavaScript rendering or use an unlisted board.\n"
        f"Suggestion: search '{company_name} careers jobs' manually, then call\n"
        f"  update_career_page_url('{company_name}', '<correct url>')\n"
        f"to save the fix."
    )


def update_career_page_url(company_name: str, new_url: str) -> str:
    """Saves a corrected career page URL for a company into the overrides file.

    The override is applied automatically on the next monitor_career_pages() run.
    Nothing in the source code is changed — overrides live in career_url_overrides.json.

    Args:
        company_name: Exact company name as it appears in the monitor list.
        new_url:      The correct, working career page URL.

    Returns:
        Confirmation showing the old and new URL.
    """
    overrides = _load_overrides()
    old_url = overrides.get(company_name, "(none set)")
    overrides[company_name] = new_url
    _save_overrides(overrides)
    return (
        f"[URL Healer] Override saved for '{company_name}'.\n"
        f"  Was : {old_url}\n"
        f"  Now : {new_url}\n"
        f"Applied automatically on the next career page scan."
    )


def list_url_overrides() -> str:
    """Lists every active career page URL override currently saved.

    Returns:
        All company name → corrected URL pairs, or a message if the file is empty.
    """
    overrides = _load_overrides()
    if not overrides:
        return "No URL overrides active. All companies use their default career page URLs."
    lines = [f"  {company}: {url}" for company, url in overrides.items()]
    return f"Active URL overrides ({len(overrides)}):\n" + "\n".join(lines)
