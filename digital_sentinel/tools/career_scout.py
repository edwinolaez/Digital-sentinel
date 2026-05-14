"""
Digital Sentinel — Career Scout
Parses a block of email subjects (output from the email tools) and:
  1. Flags LinkedIn social noise (likes, comments, profile views) for bulk deletion.
  2. Drops bank notifications, retail ads, and promotional emails silently.
  3. Drops LinkedIn job alerts for senior/non-entry-level roles.
  4. Drops job alerts for US-only positions (Canada/remote-Canada only).
  5. Identifies entry-level software job alerts matching your SAIT tech stack.
  6. Flags emails containing scam/phishing signals.
"""
import re

from .scam_detector import scan_for_scam_signals

# ── Keyword sets ──────────────────────────────────────────────────────────────

_LEVEL_KEYWORDS = [
    "junior", "entry level", "entry-level", "intern", "internship",
    "co-op", "coop", "co op", "new grad", "graduate", "associate",
    "0-2 years", "0 to 2 years",
]

# Tech stack aligned with SAIT software development program
_TECH_KEYWORDS = [
    "next.js", "nextjs", "react", "python", "javascript", "typescript",
    "node.js", "node", "full stack", "fullstack", "full-stack",
    "frontend", "front-end", "front end", "backend", "back-end", "back end",
    "software developer", "software engineer", "web developer",
    "flask", "django", "fastapi", "rest api", "sql", "mongodb",
]

# LinkedIn social noise — not job-related
_NOISE_PATTERNS = [
    r"liked your",
    r"commented on",
    r"reacted to",
    r"viewed your profile",
    r"sent you a message",
    r"wants to connect",
    r"new connection",
    r"endorsed you",
    r"congratulate",
    r"work anniversary",
    r"birthday",
    r"is hiring",
    r"people are talking",
]

# Phrases that strongly suggest this is a job alert email
_JOB_ALERT_PATTERNS = [
    r"job alert", r"new job", r"job opening", r"job opportunity",
    r"hiring", r"position available", r"we.re looking", r"apply now",
    r"posted a job", r"matches your",
]

# ── Filters — emails that are silently dropped from the brief ─────────────────

# Bank notifications, retail ads, and promotional emails
_COMMERCIAL_NOISE_RE = re.compile(
    r"\b(sale|% off|promo|discount|coupon|shop now|limited time|clearance|"
    r"flash sale|free shipping|order confirmation|your order|your shipment|"
    r"has shipped|tracking number|delivery update|"
    r"transaction alert|account statement|account activity|account alert|"
    r"e-transfer|interac|payment received|payment processed|payment confirmation|"
    r"invoice|receipt|your bill|bill is ready|bank statement|new statement|"
    r"credit card statement|statement available|earn points|reward points|"
    r"cashback|loyalty reward|special offer|exclusive offer|don.t miss|"
    r"act now|today only|hours only|unsubscribe)\b",
    re.IGNORECASE,
)

# Senders that are always commercial noise (matched against the From field)
_COMMERCIAL_SENDERS_RE = re.compile(
    r"(noreply@|no-reply@|notifications?@|marketing@|promo@|offers?@|"
    r"deals?@|newsletter@|updates?@|news@|info@.*\.(retail|shop|store|bank|"
    r"financial|insurance|credit))",
    re.IGNORECASE,
)

# Senior / leadership level — if present in a job alert, drop it
_SENIOR_RE = re.compile(
    r"\b(senior|sr\b|sr\.|lead\b|principal|staff engineer|architect|"
    r"manager|director|head of|vp\b|vice president|cto|cso|chief)\b",
    re.IGNORECASE,
)

# US-only location signals
_US_LOCATION_RE = re.compile(
    r"\b(united states|usa\b|us only|u\.s\. only|us-based|"
    r"new york city|nyc\b|san francisco|los angeles|seattle|austin|"
    r"chicago|boston|denver|atlanta|dallas|miami|houston|phoenix|"
    r"portland|minneapolis|nashville|raleigh|washington dc|"
    r"remote.*us only|us.*remote only|must be.*in the (us|u\.s\.|united states))\b",
    re.IGNORECASE,
)

# Canadian location signals — if present alongside a US signal, keep the email
_CANADA_RE = re.compile(
    r"\b(canada|canadian|calgary|alberta|ab\b|vancouver|bc\b|toronto|ontario|"
    r"montreal|quebec|winnipeg|edmonton|ottawa|halifax|"
    r"remote canada|canada.wide|across canada)\b",
    re.IGNORECASE,
)


def scan_for_job_leads(email_subjects: str) -> str:
    """Scans a block of email header text for entry-level software job leads.

    Pass the combined output of fetch_gmail_emails / fetch_yahoo_emails /
    fetch_sait_emails directly into this function.

    Args:
        email_subjects: Raw multi-line string of email headers (date / from / subject).

    Returns:
        A formatted Career Scout report with matched leads, flagged noise, and a summary.
    """
    lines = [l.strip() for l in email_subjects.splitlines() if l.strip()]

    job_leads: list[tuple[str, str]] = []
    noise_flagged: list[str] = []
    scam_flagged: list[tuple[str, str]] = []  # (risk_level, line)
    dropped_commercial = 0
    dropped_senior = 0
    dropped_us = 0

    for line in lines:
        # Skip section headers like "[Gmail] 12 unread emails:"
        if line.startswith("[") and line.endswith(":"):
            continue

        ll = line.lower()

        # --- Scam check first (highest priority) ---
        scam = scan_for_scam_signals(line)
        if scam["risk"] in ("SCAM", "CAUTION"):
            scam_flagged.append((scam["risk"], line))
            continue

        # --- Commercial noise: banks, ads, retail promos (silent drop) ---
        if _COMMERCIAL_NOISE_RE.search(line) or _COMMERCIAL_SENDERS_RE.search(line):
            dropped_commercial += 1
            continue

        # --- LinkedIn social noise ---
        if any(re.search(p, ll) for p in _NOISE_PATTERNS):
            noise_flagged.append(line)
            continue

        # --- Job alert? Apply entry-level and location filters ---
        is_job_alert = any(re.search(p, ll) for p in _JOB_ALERT_PATTERNS)

        if is_job_alert:
            # Drop senior/lead/manager postings — entry-level only
            if _SENIOR_RE.search(line) and not any(kw in ll for kw in _LEVEL_KEYWORDS):
                dropped_senior += 1
                continue

            # Drop US-only postings — Canada/remote-Canada only
            if _US_LOCATION_RE.search(line) and not _CANADA_RE.search(line):
                dropped_us += 1
                continue

        # --- Job lead scoring ---
        has_level = any(kw in ll for kw in _LEVEL_KEYWORDS)
        has_tech = any(kw in ll for kw in _TECH_KEYWORDS)

        if has_level and has_tech:
            job_leads.append(("MATCH", line))
        elif is_job_alert and has_tech:
            job_leads.append(("MATCH", line))
        elif is_job_alert and has_level:
            job_leads.append(("REVIEW", line))
        elif is_job_alert:
            job_leads.append(("REVIEW", line))

    # ── Build report ──────────────────────────────────────────────────────────
    sep = "=" * 46
    report = f"\n{sep}\n CAREER SCOUT REPORT\n{sep}\n"

    if job_leads:
        report += f"\nJob Leads ({len(job_leads)} found):\n"
        for verdict, line in job_leads:
            icon = "[MATCH]" if verdict == "MATCH" else "[REVIEW]"
            report += f"  {icon} {line}\n"
    else:
        report += "\nNo job leads detected in this batch.\n"

    if scam_flagged:
        report += f"\n[!] SCAM / PHISHING ALERTS ({len(scam_flagged)}) — Do NOT click these:\n"
        for risk, item in scam_flagged:
            report += f"  [{risk}] {item}\n"

    if noise_flagged:
        report += f"\nLinkedIn Noise Flagged for Deletion ({len(noise_flagged)}):\n"
        for item in noise_flagged[:15]:
            report += f"  - {item}\n"
        if len(noise_flagged) > 15:
            report += f"  ... and {len(noise_flagged) - 15} more.\n"

    matches = sum(1 for v, _ in job_leads if v == "MATCH")
    reviews = sum(1 for v, _ in job_leads if v == "REVIEW")
    dropped_total = dropped_commercial + dropped_senior + dropped_us
    report += (
        f"\nSummary: {matches} strong match(es), {reviews} to review, "
        f"{len(scam_flagged)} scam alert(s), {len(noise_flagged)} LinkedIn noise item(s) flagged.\n"
    )
    if dropped_total:
        report += (
            f"Filtered out (not shown): {dropped_commercial} bank/promo/retail, "
            f"{dropped_senior} senior-level, {dropped_us} US-only.\n"
        )
    report += f"{sep}\n"
    return report
