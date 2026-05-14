"""
Digital Sentinel — Job Board Scout
Fetches live software job postings from RemoteOK, Arbeitnow, and Canada Job Bank.
Canada Job Bank is the primary resource recommended by SAIT career advisors,
the Centre for Newcomers, CCIS, and other Calgary employment support services.
Every posting is scanned for scam signals before being surfaced.
"""
import re
import xml.etree.ElementTree as ET

import requests

from .scam_detector import scan_for_scam_signals

_HEADERS = {"User-Agent": "Digital-Sentinel/1.0 (job-search-tool)"}

_LEVEL_RE = re.compile(
    r"\b(junior|entry.level|entry level|intern|internship|co.op|coop|"
    r"new.grad|new grad|graduate|associate|0.2 years|0 to 2)\b",
    re.IGNORECASE,
)

# Explicitly senior / leadership roles — excluded from all results
_SENIOR_RE = re.compile(
    r"\b(senior|sr\.|lead|principal|staff|architect|manager|director|"
    r"head of|vp |vice president|cto|cso|chief)\b",
    re.IGNORECASE,
)

_BA_RE = re.compile(
    r"\b(business analyst|business analysis|systems analyst|data analyst|"
    r"requirements analyst|product analyst|operations analyst|"
    r"process analyst|it analyst)\b",
    re.IGNORECASE,
)

_FRONTEND_RE = re.compile(
    r"\b(frontend|front.end|front end|react|next\.?js|typescript|javascript|"
    r"ui developer|ux developer|web developer|ui engineer)\b",
    re.IGNORECASE,
)

_BACKEND_RE = re.compile(
    r"\b(backend|back.end|back end|python|node\.?js|flask|fastapi|django|"
    r"rest api|api developer|server.side|software engineer|software developer)\b",
    re.IGNORECASE,
)

_TECH_RE = re.compile(
    r"\b(python|react|typescript|javascript|next\.?js|node\.?js|"
    r"fullstack|full.stack|full stack|frontend|front.end|backend|back.end|"
    r"software developer|software engineer|web developer|"
    r"flask|fastapi|django|rest api|sql|mongodb|business analyst|analyst)\b",
    re.IGNORECASE,
)

# Job Bank Canada RSS — two complementary searches to widen the net
_JOB_BANK_SEARCHES = [
    {"searchstring": "software developer", "locationstring": "Calgary", "fprov": "AB"},
    {"searchstring": "web developer",      "locationstring": "Calgary", "fprov": "AB"},
]

# Eluta.ca — Canadian job aggregator, Calgary-focused searches
_ELUTA_SEARCHES = [
    {"q": "software developer", "l": "Calgary, AB"},
    {"q": "web developer",      "l": "Calgary, AB"},
    {"q": "junior developer",   "l": "Calgary, AB"},
]

# Browser User-Agent — Eluta.ca requires it for search pages
_ELUTA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Career support organizations whose advisors direct clients to Job Bank and
# these boards — surfaced as a resource block at the bottom of every report
_CAREER_SUPPORT_RESOURCES = """\
── Career Support Resources (Calgary & Canada) ──

The following free services are used by SAIT career advisors, newcomer
centres, and immigrant employment programs to help job seekers find roles.

  Canada Job Bank (live above)  https://www.jobbank.gc.ca
  Eluta.ca (live above)         https://www.eluta.ca
  SAIT Career Services          https://www.sait.ca/student-life/student-services/career-services
  Centre for Newcomers Calgary  https://www.centrefornewcomers.ca
  Calgary Catholic Immigration Society (CCIS)  https://www.ccis-calgary.ab.ca
  ACCES Employment              https://accesemployment.ca
  Alberta Supports              https://www.alberta.ca/alberta-supports
  Calgary Economic Development  https://calgaryeconomicdevelopment.com
"""

# Priority order: BA → FRONTEND → BACKEND → MATCH (other entry-level) → REVIEW
_PRIORITY_ORDER = ["BA", "FRONTEND", "BACKEND", "MATCH", "REVIEW"]

_PRIORITY_LABELS = {
    "BA":       "Business Analyst",
    "FRONTEND": "Frontend",
    "BACKEND":  "Backend",
    "MATCH":    "Other Entry-Level Software Dev",
    "REVIEW":   "Worth Reviewing (no explicit level signal)",
}


def _score(text: str) -> str | None:
    if _SENIOR_RE.search(text):
        return None  # Drop senior / lead / manager roles entirely

    has_level = bool(_LEVEL_RE.search(text))
    is_ba       = bool(_BA_RE.search(text))
    is_frontend = bool(_FRONTEND_RE.search(text))
    is_backend  = bool(_BACKEND_RE.search(text))
    has_tech    = bool(_TECH_RE.search(text))

    if has_level:
        if is_ba:
            return "BA"
        if is_frontend:
            return "FRONTEND"
        if is_backend:
            return "BACKEND"
        if has_tech:
            return "MATCH"
    elif is_ba or is_frontend or is_backend or has_tech:
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


def _fetch_job_bank_canada() -> list[dict]:
    """Fetches Calgary software/web developer postings from Canada Job Bank via RSS."""
    results: list[dict] = []
    seen_urls: set[str] = set()

    for params in _JOB_BANK_SEARCHES:
        try:
            resp = requests.get(
                "https://www.jobbank.gc.ca/jobsearch/rss",
                params={**params, "lang": "eng"},
                headers=_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                def _t(tag: str) -> str:
                    el = item.find(tag)
                    return (el.text or "").strip() if el is not None else ""

                raw_title = _t("title")
                url = _t("link")

                if not raw_title or url in seen_urls:
                    continue
                seen_urls.add(url)

                # Job Bank titles: "Software Developer - Acme Corp - Calgary, AB"
                parts = [p.strip() for p in raw_title.split(" - ")]
                job_title = parts[0] if parts else raw_title
                company = parts[1] if len(parts) > 1 else "Unknown"

                results.append({
                    "position": job_title,
                    "company": company,
                    "url": url,
                    "tags": ["Calgary", "AB", "Job Bank Canada"],
                })

        except ET.ParseError as e:
            results.append({"_error": f"Job Bank Canada: RSS parse error — {e}"})
        except Exception as e:
            results.append({"_error": f"Job Bank Canada: {e}"})
            break  # One network error covers both searches

    return results or [{"_error": "Job Bank Canada: No results returned"}]


def _fetch_eluta() -> list[dict]:
    """Fetches Calgary software job postings from Eluta.ca (Canadian job aggregator).

    Eluta.ca aggregates directly from employer career pages, so it surfaces roles
    that never appear on LinkedIn or international boards. Individual job links use
    client-side JavaScript routing, so the URL returned is the Eluta.ca search URL
    for that query — clicking it lands on the live results page.
    """
    results: list[dict] = []
    seen: set[str] = set()

    # Regex patterns to extract job data from server-rendered HTML
    # Eluta renders anchor tags with job titles — href may be "#!" (JS-routed)
    # but the text content is always in the HTML source.
    _title_re = re.compile(
        r'<a\b[^>]*href="[^"]*"[^>]*>\s*([A-Z][^<]{4,100}?)\s*</a>',
        re.IGNORECASE,
    )
    _company_re = re.compile(
        r'<a\b[^>]*title="See all jobs at ([^"]{2,80})"',
        re.IGNORECASE,
    )
    # Fallback: bold/strong text that follows a job title line (often company name)
    _company_fallback_re = re.compile(
        r'<(?:b|strong)[^>]*>\s*([^<]{2,80})\s*</(?:b|strong)>',
        re.IGNORECASE,
    )
    # Detect job-title-like text (contains a role keyword)
    _role_re = re.compile(
        r'\b(developer|engineer|analyst|programmer|designer|technician|'
        r'architect|administrator|specialist|coordinator|scientist)\b',
        re.IGNORECASE,
    )

    for params in _ELUTA_SEARCHES:
        search_url = (
            f"https://www.eluta.ca/search"
            f"?q={params['q'].replace(' ', '+')}"
            f"&l={params['l'].replace(' ', '+').replace(',', '%2C')}"
        )
        try:
            resp = requests.get(
                "https://www.eluta.ca/search",
                params={**params, "sort": "rank"},
                headers=_ELUTA_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            html = resp.text

            # Extract all company names via Eluta's consistent title attribute
            companies = _company_re.findall(html)

            # Extract all anchor text that looks like a job title
            all_anchors = _title_re.findall(html)
            job_titles = [
                t.strip() for t in all_anchors
                if _role_re.search(t) and 8 < len(t.strip()) < 120
            ]

            # Pair titles with companies — they appear in the same order on page
            for i, title in enumerate(job_titles):
                dedup = title.lower()
                if dedup in seen:
                    continue
                seen.add(dedup)

                company = companies[i] if i < len(companies) else "See listing"

                results.append({
                    "position": title,
                    "company":  company,
                    "url":      search_url,
                    "tags":     ["Calgary", "AB", "Eluta.ca", "Canada"],
                })

        except Exception as e:
            results.append({"_error": f"Eluta.ca ({params['q']}): {e}"})

    return results or [{"_error": "Eluta.ca: No results returned"}]


def _format_job(source: str, title: str, company: str, tags: str, url: str, scam_risk: str = "CLEAR") -> str:
    risk_tag = "" if scam_risk == "CLEAR" else f"  [!] SCAM RISK: {scam_risk}\n"
    return (
        f"  [{source}] {title}  @  {company}\n"
        f"    Tags : {tags or 'none'}\n"
        f"    URL  : {url}\n"
        f"{risk_tag}"
    ).rstrip()


def fetch_job_board_postings(max_results: int = 60) -> str:
    """Fetches fresh entry-level software job postings from three sources:
    RemoteOK, Arbeitnow, and Canada Job Bank (Calgary/AB).

    Canada Job Bank is the primary resource recommended by SAIT career advisors,
    the Centre for Newcomers, CCIS, ACCES Employment, and other Calgary
    employment support services. It surfaces local Calgary postings that rarely
    appear on LinkedIn or the international boards.

    Postings are scored against Edwin's stack (Python, React, TypeScript,
    Next.js, Node.js) and tagged as MATCH (level + tech match) or REVIEW
    (tech match only). A career support resources section is always appended.

    Args:
        max_results: Maximum number of scored postings to return (default 60).

    Returns:
        Scored and labelled job listings grouped by verdict, with source,
        tags, and direct URLs, plus a career support resources block.
    """
    sources = [
        ("RemoteOK",          _fetch_remoteok()),
        ("Arbeitnow",         _fetch_arbeitnow()),
        ("Job Bank Canada",   _fetch_job_bank_canada()),
        ("Eluta.ca",          _fetch_eluta()),
    ]

    buckets: dict[str, list[str]] = {p: [] for p in _PRIORITY_ORDER}
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
            buckets[verdict].append(formatted)
            count += 1

    sep = "=" * 46
    report = f"\n{sep}\n JOB BOARD SCOUT  (RemoteOK · Arbeitnow · Job Bank Canada · Eluta.ca)\n{sep}\n"
    report += "\nPriority: Business Analyst → Frontend → Backend → Other Entry-Level → Reviewing\n"

    any_results = False
    for priority in _PRIORITY_ORDER:
        entries = buckets[priority]
        if not entries:
            continue
        any_results = True
        label = _PRIORITY_LABELS[priority]
        shown = entries if priority != "REVIEW" else entries[:8]
        report += f"\n── {label} ({len(entries)}) ──\n\n"
        report += "\n\n".join(shown) + "\n"
        if priority == "REVIEW" and len(entries) > 8:
            report += f"  ... and {len(entries) - 8} more.\n"

    if not any_results:
        report += "\nNo matching postings found. Try again later — both boards update frequently.\n"

    if errors:
        report += "\nSource errors:\n" + "\n".join(errors) + "\n"

    totals = {p: len(buckets[p]) for p in _PRIORITY_ORDER}
    report += (
        f"\nSummary: {totals['BA']} BA · {totals['FRONTEND']} Frontend · "
        f"{totals['BACKEND']} Backend · {totals['MATCH']} other entry-level · "
        f"{totals['REVIEW']} to review — sourced from RemoteOK, Arbeitnow, Job Bank Canada, and Eluta.ca.\n"
    )
    report += f"{sep}\n"
    report += f"\n{_CAREER_SUPPORT_RESOURCES}"
    report += f"{sep}\n"
    return report
