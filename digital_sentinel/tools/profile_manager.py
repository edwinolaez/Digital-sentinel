"""
Digital Sentinel — Profile Manager
Stores and manages Edwin's personal profile: background, projects, skills,
goals, and preferences. Acts as the single source of truth for all agents.
"""
import json
import os
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_PROFILE_PATH = os.path.join(_PROJECT_ROOT, "profile.json")

# ── Default profile (pre-populated with known info) ───────────────────────────

_DEFAULT_PROFILE = {
    "personal": {
        "name": "Edwin Olaez",
        "location": "Calgary, AB",
        "email": "edwinolaez@yahoo.com",
        "linkedin": "",
        "github": "",
        "portfolio": ""
    },
    "education": {
        "institution": "Southern Alberta Institute of Technology (SAIT)",
        "program": "Software Development",
        "graduation": "August 2026",
        "gpa": ""
    },
    "skills": {
        "languages":  ["Python", "TypeScript", "JavaScript"],
        "frontend":   ["React", "Next.js", "HTML", "CSS"],
        "backend":    ["Node.js", "Flask", "FastAPI"],
        "databases":  ["SQL", "MongoDB"],
        "tools":      ["Git", "GitHub", "VS Code", "Google ADK", "Gemini API"],
        "other":      ["REST APIs", "OAuth 2.0", "IMAP/SSL", "Multi-agent systems"]
    },
    "projects": [
        {
            "name": "Digital Sentinel",
            "description": "Multi-agent AI personal assistant using Google ADK and Gemini 2.5 Flash. Handles email career scouting, GitHub security auditing, trend intelligence, job hunting, resume coaching, and cold outreach drafting.",
            "tech": ["Python", "Google ADK", "Gemini 2.5 Flash", "Gmail API", "GitHub API", "RemoteOK API"],
            "url": "",
            "highlights": [
                "5 specialized sub-agents with ParallelAgent fan-out",
                "Real-time scam detection on all job postings and URLs",
                "Token usage tracking with cost estimation"
            ]
        },
        {
            "name": "CAF C2 System",
            "description": "Real-time command and control system for drone telemetry built at a hackathon. Uses MAVLink protocol over multicast UDP with a live dashboard showing drone state, position, and mission status.",
            "tech": ["Python", "MAVLink", "React", "Multicast UDP"],
            "url": "",
            "highlights": [
                "Built under hackathon time pressure — fully functional",
                "Real-time telemetry over MAVLink protocol",
                "Live mission status dashboard"
            ]
        },
        {
            "name": "Wildfire Intelligence Crew",
            "description": "Global fire monitoring system using satellite data feeds with a REST API backend and frontend dashboard for real-time data ingestion and alerting.",
            "tech": ["Python", "REST API", "Dashboard"],
            "url": "",
            "highlights": [
                "Real-time satellite data ingestion",
                "Global fire monitoring and alerting"
            ]
        }
    ],
    "goals": {
        "short_term": "Land first software development role by October 2026",
        "long_term": "Become a full-stack developer specializing in AI-powered applications",
        "target_roles": ["Junior Software Developer", "Junior Full-Stack Developer", "Junior Frontend Developer"],
        "target_companies": ["Neo Financial", "Bold Commerce", "Benevity", "Helcim", "Jobber"],
        "preferred_stack": ["Next.js", "Python", "React", "TypeScript"]
    },
    "preferences": {
        "work_type": ["hybrid", "remote"],
        "location": "Calgary, AB (open to remote Canada-wide)",
        "salary_expectation": "",
        "company_size": ["startup", "mid-size", "enterprise"]
    },
    "interests": {
        "technical": ["AI/ML", "multi-agent systems", "full-stack web development", "open source"],
        "personal":  []
    },
    "notes": "",
    "_last_updated": ""
}


# ── Persistence ───────────────────────────────────────────────────────────────

def _load() -> dict:
    if os.path.exists(_PROFILE_PATH):
        with open(_PROFILE_PATH) as f:
            return json.load(f)
    # First run — seed with defaults and save
    _save(_DEFAULT_PROFILE.copy())
    return _DEFAULT_PROFILE.copy()


def _save(profile: dict) -> None:
    profile["_last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with open(_PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def _get_nested(obj: dict, path: str):
    """Traverse a dot-notation path like 'goals.short_term'."""
    parts = path.split(".")
    for p in parts:
        if not isinstance(obj, dict) or p not in obj:
            return None
        obj = obj[p]
    return obj


def _set_nested(obj: dict, path: str, value) -> bool:
    """Set a value at a dot-notation path. Returns False if path not found."""
    parts = path.split(".")
    for p in parts[:-1]:
        if p not in obj or not isinstance(obj[p], dict):
            return False
        obj = obj[p]
    if parts[-1] not in obj:
        return False
    obj[parts[-1]] = value
    return True


# ── Formatting ────────────────────────────────────────────────────────────────

def _format_profile(p: dict) -> str:
    sep = "=" * 50
    out = f"\n{sep}\n DIGITAL SENTINEL — YOUR PROFILE\n{sep}\n"

    # Personal
    pr = p.get("personal", {})
    out += f"\nPERSONAL\n"
    out += f"  Name      : {pr.get('name', '')}\n"
    out += f"  Location  : {pr.get('location', '')}\n"
    out += f"  Email     : {pr.get('email', '')}\n"
    out += f"  LinkedIn  : {pr.get('linkedin') or '(not set)'}\n"
    out += f"  GitHub    : {pr.get('github') or '(not set)'}\n"
    out += f"  Portfolio : {pr.get('portfolio') or '(not set)'}\n"

    # Education
    ed = p.get("education", {})
    out += f"\nEDUCATION\n"
    out += f"  {ed.get('program', '')} — {ed.get('institution', '')}\n"
    out += f"  Graduating: {ed.get('graduation', '')}\n"
    if ed.get("gpa"):
        out += f"  GPA: {ed['gpa']}\n"

    # Skills
    sk = p.get("skills", {})
    out += f"\nSKILLS\n"
    for category, items in sk.items():
        if items:
            out += f"  {category.capitalize():10s}: {', '.join(items)}\n"

    # Projects
    projects = p.get("projects", [])
    out += f"\nPROJECTS ({len(projects)})\n"
    for i, proj in enumerate(projects, 1):
        out += f"\n  {i}. {proj.get('name', 'Unnamed')}\n"
        out += f"     {proj.get('description', '')}\n"
        if proj.get("tech"):
            out += f"     Tech      : {', '.join(proj['tech'])}\n"
        if proj.get("url"):
            out += f"     URL       : {proj['url']}\n"
        if proj.get("highlights"):
            out += "     Highlights:\n"
            for h in proj["highlights"]:
                out += f"       · {h}\n"

    # Goals
    gl = p.get("goals", {})
    out += f"\nGOALS\n"
    out += f"  Short-term  : {gl.get('short_term', '')}\n"
    out += f"  Long-term   : {gl.get('long_term', '')}\n"
    if gl.get("target_roles"):
        out += f"  Target roles: {', '.join(gl['target_roles'])}\n"
    if gl.get("target_companies"):
        out += f"  Target cos  : {', '.join(gl['target_companies'])}\n"
    if gl.get("preferred_stack"):
        out += f"  Pref. stack : {', '.join(gl['preferred_stack'])}\n"

    # Preferences
    pf = p.get("preferences", {})
    out += f"\nPREFERENCES\n"
    out += f"  Work type   : {', '.join(pf.get('work_type', []))}\n"
    out += f"  Location    : {pf.get('location', '')}\n"
    if pf.get("salary_expectation"):
        out += f"  Salary      : {pf['salary_expectation']}\n"
    if pf.get("company_size"):
        out += f"  Company size: {', '.join(pf['company_size'])}\n"

    # Interests
    intr = p.get("interests", {})
    if intr.get("technical"):
        out += f"\nINTERESTS (Technical)\n"
        out += f"  {', '.join(intr['technical'])}\n"
    if intr.get("personal"):
        out += f"\nINTERESTS (Personal)\n"
        out += f"  {', '.join(intr['personal'])}\n"

    # Notes
    if p.get("notes"):
        out += f"\nNOTES\n  {p['notes']}\n"

    out += f"\n  Last updated: {p.get('_last_updated', 'never')}\n"
    out += f"{sep}\n"
    return out


# ── Public tools ──────────────────────────────────────────────────────────────

def get_profile() -> str:
    """Returns Edwin's full profile: personal info, education, skills, projects,
    goals, preferences, and interests.

    All agents call this to get up-to-date background information instead of
    relying on hardcoded text. Always call this at the start of resume coaching
    or cold outreach drafting.

    Returns:
        Formatted profile with all sections.
    """
    return _format_profile(_load())


def set_profile_field(path: str, value: str) -> str:
    """Updates a single field in the profile using dot notation.

    Use this for simple string fields. For lists (skills, interests, roles),
    use add_to_list() or remove_from_list() instead.

    Valid paths (examples):
      personal.name          personal.location       personal.email
      personal.linkedin      personal.github         personal.portfolio
      education.graduation   education.gpa
      goals.short_term       goals.long_term
      preferences.location   preferences.salary_expectation
      notes

    Args:
        path : Dot-notation field path (e.g. 'personal.linkedin').
        value: New value to set.

    Returns:
        Confirmation or error message.
    """
    profile = _load()
    # Handle top-level fields like "notes"
    if "." not in path:
        if path in profile:
            profile[path] = value
            _save(profile)
            return f"[Profile] Updated '{path}' = '{value}'"
        return f"[Profile] Field '{path}' not found. Use dot notation like 'personal.linkedin'."

    if _set_nested(profile, path, value):
        _save(profile)
        return f"[Profile] Updated '{path}' = '{value}'"
    return (
        f"[Profile] Could not find field '{path}'. "
        f"Check the path — e.g. 'personal.linkedin', 'goals.short_term'."
    )


def add_to_list(path: str, item: str) -> str:
    """Adds an item to a list field in the profile.

    Valid list paths:
      skills.languages      skills.frontend       skills.backend
      skills.databases      skills.tools          skills.other
      goals.target_roles    goals.target_companies goals.preferred_stack
      preferences.work_type preferences.company_size
      interests.technical   interests.personal

    Args:
        path: Dot-notation path to a list field (e.g. 'skills.languages').
        item: The item to add (e.g. 'Go', 'Docker').

    Returns:
        Confirmation or error message.
    """
    profile = _load()
    current = _get_nested(profile, path)
    if current is None:
        return f"[Profile] List field '{path}' not found."
    if not isinstance(current, list):
        return f"[Profile] '{path}' is not a list field. Use set_profile_field() instead."
    if item in current:
        return f"[Profile] '{item}' is already in {path}."
    current.append(item)
    _set_nested(profile, path, current)
    _save(profile)
    return f"[Profile] Added '{item}' to {path}."


def remove_from_list(path: str, item: str) -> str:
    """Removes an item from a list field in the profile.

    Args:
        path: Dot-notation path to a list field (e.g. 'skills.languages').
        item: The item to remove.

    Returns:
        Confirmation or error message.
    """
    profile = _load()
    current = _get_nested(profile, path)
    if current is None:
        return f"[Profile] List field '{path}' not found."
    if not isinstance(current, list):
        return f"[Profile] '{path}' is not a list field."
    if item not in current:
        return f"[Profile] '{item}' not found in {path}."
    current.remove(item)
    _set_nested(profile, path, current)
    _save(profile)
    return f"[Profile] Removed '{item}' from {path}."


def add_project(name: str, description: str, tech: str, url: str = "", highlights: str = "") -> str:
    """Adds a new project to the profile.

    Args:
        name        : Project name (e.g. 'Portfolio Website').
        description : What it does and why it's interesting.
        tech        : Comma-separated list of technologies used.
        url         : Live URL or GitHub link (optional).
        highlights  : Comma-separated list of key achievements (optional).

    Returns:
        Confirmation message.
    """
    profile = _load()
    projects = profile.get("projects", [])

    # Check for duplicates
    if any(p["name"].lower() == name.lower() for p in projects):
        return f"[Profile] A project named '{name}' already exists. Use update_project() to edit it."

    tech_list = [t.strip() for t in tech.split(",") if t.strip()]
    highlight_list = [h.strip() for h in highlights.split(",") if h.strip()] if highlights else []

    projects.append({
        "name": name,
        "description": description,
        "tech": tech_list,
        "url": url,
        "highlights": highlight_list
    })
    profile["projects"] = projects
    _save(profile)
    return f"[Profile] Project '{name}' added (tech: {', '.join(tech_list)})."


def update_project(name: str, field: str, value: str) -> str:
    """Updates a field on an existing project.

    Args:
        name  : Project name to update (must match exactly).
        field : Field to update — one of: description, tech, url, highlights.
                For 'tech' and 'highlights', provide a comma-separated list.
        value : New value for the field.

    Returns:
        Confirmation or error message.
    """
    profile = _load()
    projects = profile.get("projects", [])
    for proj in projects:
        if proj["name"].lower() == name.lower():
            if field in ("tech", "highlights"):
                proj[field] = [v.strip() for v in value.split(",") if v.strip()]
            elif field in ("description", "url"):
                proj[field] = value
            else:
                return f"[Profile] Unknown project field '{field}'. Use: description, tech, url, highlights."
            profile["projects"] = projects
            _save(profile)
            return f"[Profile] Updated '{field}' on project '{proj['name']}'."
    return f"[Profile] Project '{name}' not found. Check the name matches exactly."


def remove_project(name: str) -> str:
    """Removes a project from the profile by name.

    Args:
        name: Project name to remove (must match exactly).

    Returns:
        Confirmation or error message.
    """
    profile = _load()
    projects = profile.get("projects", [])
    before = len(projects)
    profile["projects"] = [p for p in projects if p["name"].lower() != name.lower()]
    if len(profile["projects"]) == before:
        return f"[Profile] Project '{name}' not found."
    _save(profile)
    return f"[Profile] Project '{name}' removed."
