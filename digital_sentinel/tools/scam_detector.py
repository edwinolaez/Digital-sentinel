"""
Digital Sentinel — Scam Detector
Detects job posting scam signals and validates URLs against known safe domains.
Used internally by job_board_scout, fetch_job_posting, and career_scout.
"""
import re
from urllib.parse import urlparse

# ── Known safe job board and company career page domains ─────────────────────
# Any URL whose root domain matches one of these is considered structurally safe.
_SAFE_DOMAINS: set[str] = {
    # Job boards
    "linkedin.com", "indeed.com", "glassdoor.com", "wellfound.com",
    "angel.co", "remoteok.com", "arbeitnow.com", "weworkremotely.com",
    "workatastartup.com", "hired.com", "simplyhired.com", "ziprecruiter.com",
    "monster.com", "workopolis.com", "jobbank.gc.ca",
    # ATS platforms (where real companies post jobs)
    "lever.co", "greenhouse.io", "workday.com", "myworkdayjobs.com",
    "icims.com", "smartrecruiters.com", "taleo.net", "successfactors.com",
    "bamboohr.com", "jobvite.com", "recruitee.com", "ashbyhq.com",
    "jobs.lever.co", "boards.greenhouse.io",
    # Canadian job boards
    "ca.indeed.com", "eluta.ca", "neuvoo.ca", "talent.com",
    # Government
    "canada.ca", "alberta.ca",
    # Known Calgary tech companies (from our monitored list)
    "neofinancial.com", "boldcommerce.com", "benevity.com", "symend.com",
    "attabotics.com", "miovision.com", "helcim.com", "showpass.com",
    "arcurve.com", "1password.com", "getjobber.com", "trulioo.com",
}

# ── Suspicious TLDs often used in scam/phishing sites ────────────────────────
_SUSPICIOUS_TLDS: set[str] = {
    ".tk", ".ml", ".ga", ".cf", ".gq",   # Free Freenom TLDs — almost never legit
    ".xyz", ".top", ".click", ".loan",
    ".work", ".bid", ".win", ".trade",
}

# ── Job scam content patterns ─────────────────────────────────────────────────

# These phrases in a job posting are strong scam signals
_SCAM_STRONG = [
    r"\bcryptocurrency\b", r"\bbitcoin\b", r"\bcrypto\s+pay", r"\bwire\s+transfer\b",
    r"\bmoney\s+order\b", r"\bgift\s+card\b",
    r"\bsend\s+payment\b", r"\bpay\s+for\s+training\b", r"\bpurchase\s+(your\s+)?equipment\b",
    r"\bstarter\s+kit\b", r"\brefundable\s+deposit\b",
    r"\bwork\s+from\s+home\b.{0,80}\b(no\s+experience|anyone\s+can)\b",
    r"\bearn\s+\$\d{3,}\s+per\s+(day|hour)\b",
    r"\b(reshipping|re-shipping)\b", r"\bpackage\s+handler\b",
    r"\bmlm\b", r"\bmulti.level\s+marketing\b", r"\bbe\s+your\s+own\s+boss\b",
    r"\bunlimited\s+earning\s+potential\b",
    r"\bno\s+interview\s+(required|needed)\b",
    r"\bhired\s+(immediately|on\s+the\s+spot|same\s+day)\b",
    r"\bsend\s+(your\s+)?(social\s+security|ssn|sin\s+number|bank\s+account)\b",
]

# These phrases are soft signals — suspicious when combined with others
_SCAM_SOFT = [
    r"\bwork\s+from\s+home\b", r"\bremote\b.{0,40}\bno\s+experience\b",
    r"\bimmediately\s+(hiring|available)\b", r"\burgent\s+hiring\b",
    r"\bno\s+experience\s+(necessary|required|needed)\b",
    r"\bflexible\s+hours\b.{0,60}\bhigh\s+(pay|salary|income)\b",
    r"\b(very\s+)?(easy|simple)\s+(work|job|task)s?\b",
    r"\bpassive\s+income\b", r"\bfinancial\s+freedom\b",
    r"\bwork\s+(whenever|anywhere)\s+you\s+want\b",
    r"\bno\s+degree\s+required\b.{0,60}\b\$[5-9]\d{4,}\b",  # "no degree needed" + $50k+/yr sounds fine but "$500/day" is suspicious
    r"\bcontact\s+us\s+(on\s+)?whatsapp\b", r"\btelegram\b.{0,30}\bjob\b",
]

_STRONG_RE = [re.compile(p, re.IGNORECASE) for p in _SCAM_STRONG]
_SOFT_RE = [re.compile(p, re.IGNORECASE) for p in _SCAM_SOFT]


# ── Public functions ──────────────────────────────────────────────────────────

def check_url_safety(url: str) -> dict:
    """Checks whether a URL is from a known safe domain or shows suspicious signals.

    Args:
        url: The URL to check.

    Returns:
        dict with keys:
            safe (bool)     — True if the domain is known-safe
            risk (str)      — "SAFE", "UNKNOWN", or "SUSPICIOUS"
            reasons (list)  — List of reasons for a non-SAFE verdict
    """
    reasons: list[str] = []

    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        hostname = parsed.hostname or ""
        scheme = parsed.scheme
    except Exception:
        return {"safe": False, "risk": "SUSPICIOUS", "reasons": ["Could not parse URL"]}

    # Strip leading 'www.'
    root = hostname.removeprefix("www.")

    # Check against safe domain list (exact match or subdomain of safe domain)
    is_known_safe = any(
        root == safe or root.endswith(f".{safe}")
        for safe in _SAFE_DOMAINS
    )

    if is_known_safe:
        return {"safe": True, "risk": "SAFE", "reasons": []}

    # Not in safe list — check for red flags
    if scheme == "http":
        reasons.append("Uses HTTP (not HTTPS) — no encryption")

    tld = "." + root.rsplit(".", 1)[-1] if "." in root else ""
    if tld in _SUSPICIOUS_TLDS:
        reasons.append(f"Suspicious TLD '{tld}' — commonly used in scam sites")

    # Typosquatting check: does it look like a known domain with a typo?
    _TYPO_TARGETS = ["linkedin", "indeed", "glassdoor", "greenhouse", "workday"]
    for target in _TYPO_TARGETS:
        if target in root and root != target and not root.endswith(f".{target}.com"):
            reasons.append(f"Domain contains '{target}' but isn't the real site — possible typosquatting")
            break

    # Excessively long or hyphen-heavy domains are a phishing signal
    if len(root) > 40:
        reasons.append("Unusually long domain name — phishing signal")
    if root.count("-") >= 3:
        reasons.append("Excessive hyphens in domain — phishing signal")

    risk = "SUSPICIOUS" if reasons else "UNKNOWN"
    return {"safe": is_known_safe, "risk": risk, "reasons": reasons}


def scan_for_scam_signals(text: str) -> dict:
    """Scans job posting text for scam and fraud indicators.

    Args:
        text: Raw job posting text (title + description).

    Returns:
        dict with keys:
            risk (str)           — "CLEAR", "CAUTION", or "SCAM"
            strong_hits (list)   — Matched strong scam patterns
            soft_hits (list)     — Matched soft scam patterns
            summary (str)        — One-line verdict
    """
    ll = text.lower()

    strong_hits = [p.pattern for p in _STRONG_RE if p.search(ll)]
    soft_hits = [p.pattern for p in _SOFT_RE if p.search(ll)]

    if strong_hits:
        risk = "SCAM"
        summary = f"SCAM — {len(strong_hits)} strong fraud signal(s) detected. Do not apply."
    elif len(soft_hits) >= 3:
        risk = "CAUTION"
        summary = f"CAUTION — {len(soft_hits)} soft signals. Research this company before applying."
    elif len(soft_hits) >= 1:
        risk = "CAUTION"
        summary = f"CAUTION — {len(soft_hits)} soft signal(s). Verify the company is legitimate."
    else:
        risk = "CLEAR"
        summary = "CLEAR — No scam signals detected."

    return {
        "risk": risk,
        "strong_hits": strong_hits,
        "soft_hits": soft_hits,
        "summary": summary,
    }


def format_safety_report(url_result: dict, scam_result: dict) -> str:
    """Formats the combined URL + content safety check into a readable block."""
    lines = [
        f"  URL Safety : {url_result['risk']}",
        f"  Job Safety : {scam_result['risk']}",
    ]
    if url_result["reasons"]:
        lines.append("  URL Flags  :")
        for r in url_result["reasons"]:
            lines.append(f"    ! {r}")
    if scam_result["strong_hits"]:
        lines.append("  Scam Flags (STRONG):")
        for h in scam_result["strong_hits"]:
            lines.append(f"    !! {h}")
    if scam_result["soft_hits"]:
        lines.append("  Scam Flags (soft):")
        for h in scam_result["soft_hits"][:5]:
            lines.append(f"    ~ {h}")
    return "\n".join(lines)
