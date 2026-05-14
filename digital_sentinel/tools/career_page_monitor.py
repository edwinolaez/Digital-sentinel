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
_OVERRIDES_PATH = os.path.join(_PROJECT_ROOT, "career_url_overrides.json")

# ── Target companies ──────────────────────────────────────────────────────────
# Calgary 100 Strategy — organized by category.
TARGET_COMPANIES: dict[str, str] = {
    # ── Original watchlist (Top 10) ──────────────────────────────────────────
    "Neo Financial":            "https://jobs.lever.co/neofinancial",
    "Bold Commerce":            "https://boldcommerce.com/careers",
    "Benevity":                 "https://benevity.com/careers",
    "Symend":                   "https://symend.com/careers",
    "Attabotics":               "https://attabotics.com/careers",
    "Miovision":                "https://miovision.com/careers",
    "Helcim":                   "https://www.helcim.com/careers",
    "Showpass":                 "https://showpass.com/about/careers",
    "Arcurve":                  "https://arcurve.com/careers",
    "1Password":                "https://jobs.lever.co/1password",
    "Jobber":                   "https://getjobber.com/careers",
    "Trulioo":                  "https://www.trulioo.com/company/careers",

    # ── High-Priority Targets (11-20) ────────────────────────────────────────
    "StellarAlgo":              "https://stellaralgo.com/careers",
    "Cathedral Energy":         "https://cathedralenergy.com/careers",
    "Stantec":                  "https://www.stantec.com/en/careers",
    "General Dynamics MS":      "https://www.gdmissionsystems.ca/careers",
    "Verano.AI":                "https://verano.ai/careers",
    "Subsurface Dynamics":      "https://ssdynamics.com/careers",
    "Knead Tech":               "https://knead.tech/careers",
    "Mikata Health":            "https://mikatahealth.com/careers",
    "North Vector Dynamics":    "https://northvector.ca/careers",
    "Ultimarii":                "https://ultimarii.com/careers",

    # ── Managed Service Providers (21-25) ────────────────────────────────────
    "F12.net":                  "https://f12.net/careers",
    "Nucleus Networks":         "https://nucleusnetworks.ca/careers",
    "GAM Tech":                 "https://www.gam-tech.ca/careers",
    "Sure Systems":             "https://suresystems.ca/careers",
    "403 IT Solutions":         "https://403it.com/careers",

    # ── Additional MSPs (26-40) ──────────────────────────────────────────────
    "Bulletproof IT":           "https://www.bulletproofsi.com/careers",
    "Microserve":               "https://microserve.ca/careers",
    "TWT Group":                "https://twtgroup.com/careers",
    "Long View Systems":        "https://www.longviewsystems.ca/careers",
    "Itergy":                   "https://itergy.com/careers",
    "CompuVision":              "https://compuvision.com/careers",
    "Managed247":               "https://managed247.com/careers",
    "Catalyst IT":              "https://catalystit.ca/careers",
    "SysGen Solutions":         "https://sysgen.ca/careers",

    # ── Fintech Startups (41-45) ─────────────────────────────────────────────
    "Cashew":                   "https://getcashew.com/careers",
    "Village Wellth":           "https://villagewellth.com/careers",
    "ZayZoon":                  "https://zayzoon.com/careers",
    "Katipult":                 "https://katipult.com/careers",
    "Shareworks (Solium)":      "https://shareworks.com/careers",

    # ── Energy / AgTech (46-50) ──────────────────────────────────────────────
    "Arolytics":                "https://arolytics.com/careers",
    "Ambyint":                  "https://ambyint.com/careers",
    "Iron Horse":               "https://ironhorse.ca/careers",
    "SensorUp":                 "https://sensorup.com/careers",

    # ── AI & Data (51-55) ────────────────────────────────────────────────────
    "AltaML":                   "https://altaml.com/careers",
    "Chata.ai":                 "https://chata.ai/careers",
    "Teradici (HP)":            "https://www.teradici.com/company/careers",
    "White Whale Analytics":    "https://whitewhaleanalytics.com/careers",

    # ── E-commerce (56-59) ───────────────────────────────────────────────────
    "LodgeLink":                "https://lodgelink.com/careers",

    # ── Public Sector (60-62) ────────────────────────────────────────────────
    "City of Calgary IT":       "https://www.calgary.ca/careers",
    "Alberta Health Services":  "https://careers.albertahealthservices.ca",
    "University of Calgary":    "https://ucalgary.ca/careers",

    # ── SAIT Industry Partners (81-90) ───────────────────────────────────────
    "Pason Systems":            "https://pason.com/careers",
    "Spartan Controls":         "https://spartancontrols.com/careers",
    "TC Energy":                "https://careers.tcenergy.com",

    # ── Digital Agencies (91-100) ────────────────────────────────────────────
    "Vog App Devs":             "https://vog.ca/careers",
    "Robots & Pencils":         "https://robotsandpencils.com/careers",
    "Evans Hunt":               "https://evanshunt.com/careers",
    "Critical Mass":            "https://www.criticalmassltd.com/careers",

    # ── Recruitment Agencies (Calgary & Canada) ───────────────────────────────
    "Adecco Canada":            "https://www.adecco.com/en-ca/job-search",
    "Robert Half":              "https://www.roberthalf.com/ca/en/find-jobs",
    "Hays Canada":              "https://www.hays.ca/job-search",
    "Randstad Canada":          "https://www.randstad.ca/",
    "S.I. Systems":             "https://www.sisystems.com/",
    "Agilus":                   "https://en.agilus.ca/jobs/jobsearch",
    "David Aplin Group":        "https://www.aplin.com/job-seekers/",
    "ManpowerGroup Canada":     "https://www.manpowergroup.com/en",
    "Raise (Ian Martin)":       "https://raise.jobs/job-search/",
    "About Staffing":           "https://aboutstaffing.com/",
    "Diversified Staffing":     "https://diversifiedstaffing.com/job-seekers/",
    "Matrix HR":                "https://matrixlabourleasing.com/pages/find-jobs",

    # ── Tech-Specific Job Boards ─────────────────────────────────────────────
    "ITjobs.ca":                "https://www.itjobs.ca/en/",
    "Tech Jobs Canada":         "https://www.techjobs.ca/en/",
    "Canadian Cybersecurity Jobs": "https://canadiancybersecurityjobs.com/",
    "IEEE Jobs":                "https://jobs.ieee.org/",

    # ── General Canadian Job Boards ───────────────────────────────────────────
    "Adzuna Canada":            "https://www.adzuna.ca/",
    "SimplyHired Canada":       "https://www.simplyhired.ca/",
    "AlbertaJobCentre":         "https://www.albertajobcentre.ca/",
    "Royal Municipalities AB":  "https://rmalberta.com/job-board/",
    "Careers Next Generation":  "https://www.careersnextgen.ca/",
    "NoDesk Canada":            "https://nodesk.co/remote-jobs/canada/",
}

_JOB_KEYWORDS = re.compile(
    r"\b(developer|engineer|software|frontend|backend|fullstack|full.stack|"
    r"python|react|typescript|javascript|node\.?js|next\.?js|junior|entry.level|"
    r"intern|co.op|new.grad|business analyst|systems analyst|data analyst|"
    r"requirements analyst|analyst)\b",
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


def _load_url_overrides() -> dict:
    if os.path.exists(_OVERRIDES_PATH):
        with open(_OVERRIDES_PATH) as f:
            return json.load(f)
    return {}


def _apply_overrides(companies: dict[str, str]) -> dict[str, str]:
    """Returns a copy of companies with any saved URL corrections applied."""
    overrides = _load_url_overrides()
    if not overrides:
        return companies
    merged = dict(companies)
    for name, url in overrides.items():
        if name in merged:
            merged[name] = url
    return merged


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
    companies = _apply_overrides(TARGET_COMPANIES)

    changed: list[str] = []
    unchanged: list[str] = []
    errors: list[str] = []

    for company, url in companies.items():
        text = _fetch_page_text(url)
        if text is None:
            errors.append(f"  {company} — could not fetch ({url})")
            # Persist the error so url_healer can read it
            snapshots[company] = {
                "error": "fetch failed — HTTP error or timeout",
                "url": url,
                "last_checked": now,
            }
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

    URLs reflect any active overrides from the URL healer.

    Returns:
        Formatted list of company names and URLs.
    """
    companies = _apply_overrides(TARGET_COMPANIES)
    lines = [f"  {name}: {url}" for name, url in companies.items()]
    return f"Monitored companies ({len(companies)}):\n" + "\n".join(lines)
