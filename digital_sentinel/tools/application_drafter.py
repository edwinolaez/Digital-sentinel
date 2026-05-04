"""
Digital Sentinel — Application Drafter
Saves cover letters and tailored resume bullets as local draft files.
Drafts land in application_drafts/ at the project root for review before sending.
"""
import os
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_DRAFTS_DIR = os.path.join(_PROJECT_ROOT, "application_drafts")


def _ensure_dir() -> None:
    os.makedirs(_DRAFTS_DIR, exist_ok=True)


def save_application_draft(
    job_title: str,
    company: str,
    cover_letter: str,
    tailored_bullets: str,
    job_url: str = "",
    notes: str = "",
) -> str:
    """Saves a complete application package (cover letter + resume bullets) to a local file.

    Call this immediately after generating an application package so Edwin can
    review it before anything is sent. Files are saved to application_drafts/
    named by date, company, and role.

    Args:
        job_title: Job title / role name.
        company: Company name.
        cover_letter: Full cover letter text generated for this posting.
        tailored_bullets: Tailored resume bullet points for this role.
        job_url: Original job posting URL (optional).
        notes: Any additional context notes (optional).

    Returns:
        Confirmation with the saved filename and next-step instructions.
    """
    _ensure_dir()

    date_str = datetime.now().strftime("%Y-%m-%d")

    def _safe(s: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)[:40]

    filename = f"{date_str}_{_safe(company)}_{_safe(job_title)}.txt"
    filepath = os.path.join(_DRAFTS_DIR, filename)

    sep = "=" * 60
    content = f"""{sep}
APPLICATION DRAFT
Company  : {company}
Role     : {job_title}
Date     : {date_str}
URL      : {job_url or 'N/A'}
{sep}

COVER LETTER
{'-' * 60}
{cover_letter.strip()}

TAILORED RESUME BULLETS
{'-' * 60}
{tailored_bullets.strip()}
"""
    if notes:
        content += f"\nNOTES\n{'-' * 60}\n{notes.strip()}\n"
    content += f"\n{sep}\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return (
        f"Draft saved: application_drafts/{filename}\n"
        f"Review the cover letter and bullets above.\n"
        f"When ready, say:\n"
        f"  'create gmail draft for {company}' — opens a ready-to-send Gmail draft\n"
        f"  'skip {company}' — pass on this one\n"
        f"  'apply at {job_url}' — visit the posting directly"
    )


def list_saved_drafts() -> str:
    """Lists all saved application draft files in application_drafts/.

    Returns:
        Numbered list of saved drafts, newest first.
    """
    _ensure_dir()
    files = sorted(
        [f for f in os.listdir(_DRAFTS_DIR) if f.endswith(".txt")],
        reverse=True,
    )
    if not files:
        return "No saved application drafts yet."
    lines = [f"  {i + 1}. {f}" for i, f in enumerate(files)]
    return f"Saved application drafts ({len(files)}):\n" + "\n".join(lines)
