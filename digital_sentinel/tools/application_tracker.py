"""
Digital Sentinel — Application Tracker
Logs job applications to a local JSON file, tracks their status,
and surfaces follow-up reminders for applications that have gone quiet.
"""
import json
import os
from datetime import datetime, timedelta

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_TRACKER_PATH = os.path.join(_PROJECT_ROOT, "applications.json")

_VALID_STATUSES = {
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "withdrew",
    "ghosted",
}

# Statuses that mean the process is still active (not closed)
_ACTIVE_STATUSES = {"applied", "phone_screen", "interview"}


# ── Persistence ───────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    if os.path.exists(_TRACKER_PATH):
        with open(_TRACKER_PATH) as f:
            return json.load(f)
    return []


def _save(data: list[dict]) -> None:
    with open(_TRACKER_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Public tools ──────────────────────────────────────────────────────────────

def log_application(
    company: str,
    role: str,
    url: str = "",
    notes: str = "",
) -> str:
    """Logs a new job application to the tracker.

    Args:
        company: Company name (e.g. "Neo Financial").
        role: Job title (e.g. "Junior Software Developer").
        url: Job posting URL (optional but recommended).
        notes: Any notes about how you found it or what to mention (optional).

    Returns:
        Confirmation message with the assigned application ID.
    """
    apps = _load()
    entry = {
        "id": len(apps) + 1,
        "company": company,
        "role": role,
        "url": url,
        "notes": notes,
        "status": "applied",
        "applied_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    apps.append(entry)
    _save(apps)
    return (
        f"[Tracker] Logged #{entry['id']}: {role} @ {company} — status: applied\n"
        f"  Applied: {entry['applied_date']}"
    )


def update_application_status(app_id: int, status: str, notes: str = "") -> str:
    """Updates the status of an existing application.

    Args:
        app_id: The application ID number (shown in log or get_applications output).
        status: New status. Must be one of:
                applied | phone_screen | interview | offer | rejected | withdrew | ghosted
        notes: Optional notes to append to the record.

    Returns:
        Confirmation of the update, or an error if the ID is not found.
    """
    if status not in _VALID_STATUSES:
        return (
            f"[Tracker] Invalid status '{status}'. "
            f"Valid options: {', '.join(sorted(_VALID_STATUSES))}"
        )

    apps = _load()
    for app in apps:
        if app["id"] == app_id:
            app["status"] = status
            app["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
            if notes:
                existing = app.get("notes", "")
                app["notes"] = f"{existing} | {notes}".strip(" |")
            _save(apps)
            return (
                f"[Tracker] #{app_id} ({app['role']} @ {app['company']}) "
                f"updated → {status}"
            )

    return f"[Tracker] Application #{app_id} not found."


def get_applications(status_filter: str = "all") -> str:
    """Returns all tracked job applications, optionally filtered by status.

    Args:
        status_filter: 'all' (default), or any valid status to filter by:
                       applied | phone_screen | interview | offer | rejected | withdrew | ghosted

    Returns:
        Formatted list of all matching applications with full details.
    """
    apps = _load()

    if not apps:
        return "[Tracker] No applications logged yet. Use log_application() to start tracking."

    if status_filter != "all":
        apps = [a for a in apps if a["status"] == status_filter]

    if not apps:
        return f"[Tracker] No applications with status '{status_filter}'."

    sep = "=" * 46
    report = f"\n{sep}\n APPLICATION TRACKER\n{sep}\n"

    for a in apps:
        report += (
            f"\n  #{a['id']}  {a['role']}  @  {a['company']}\n"
            f"     Status  : {a['status']}\n"
            f"     Applied : {a['applied_date']}    Last update: {a['last_updated']}\n"
        )
        if a.get("url"):
            report += f"     Posting : {a['url']}\n"
        if a.get("notes"):
            report += f"     Notes   : {a['notes']}\n"

    total = len(apps)
    report += f"\n{sep}\nTotal: {total} application(s)\n{sep}\n"
    return report


def flag_stale_applications(days_threshold: int = 14) -> str:
    """Flags active applications that haven't been updated in N days.

    These are likely ghosted or need a follow-up email.

    Args:
        days_threshold: Days with no update before flagging (default 14).

    Returns:
        List of applications needing attention, or a clean-bill-of-health message.
    """
    apps = _load()
    cutoff = datetime.utcnow() - timedelta(days=days_threshold)

    stale = [
        a for a in apps
        if a["status"] in _ACTIVE_STATUSES
        and datetime.strptime(a["last_updated"], "%Y-%m-%d") < cutoff
    ]

    if not stale:
        return (
            f"[Tracker] No stale applications (threshold: {days_threshold} days). "
            "All active applications are up to date."
        )

    sep = "=" * 46
    report = f"\n{sep}\n FOLLOW-UP NEEDED ({len(stale)} applications)\n{sep}\n"

    for a in stale:
        days_since = (
            datetime.utcnow() - datetime.strptime(a["last_updated"], "%Y-%m-%d")
        ).days
        report += (
            f"\n  #{a['id']}  {a['role']}  @  {a['company']}\n"
            f"     Status       : {a['status']}\n"
            f"     Days silent  : {days_since} days (applied {a['applied_date']})\n"
        )
        if a.get("url"):
            report += f"     Posting: {a['url']}\n"

    report += f"\n{sep}\n"
    return report
