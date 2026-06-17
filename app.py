"""
Digital Sentinel — Custom Gradio UI
Run with: python app.py  (from the digital-sentinel/ directory)
Serves at: http://127.0.0.1:7860
"""
import asyncio
import json
import os

import gradio as gr
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

load_dotenv()

from digital_sentinel.agent import root_agent

# ── ADK setup ─────────────────────────────────────────────────────────────────
_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="digital_sentinel",
    session_service=_session_service,
)
_APP_NAME  = "digital_sentinel"
_USER_ID   = "edwin"
_session_id: str | None = None


async def _ensure_session() -> str:
    global _session_id
    if _session_id is None:
        session = await _session_service.create_session(
            app_name=_APP_NAME, user_id=_USER_ID
        )
        _session_id = session.id
    return _session_id


async def _call_agent(message: str) -> str:
    sid = await _ensure_session()
    parts: list[str] = []
    async for event in _runner.run_async(
        user_id=_USER_ID,
        session_id=sid,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=message)],
        ),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for p in event.content.parts:
                if getattr(p, "text", None):
                    parts.append(p.text)
    return "\n".join(parts) if parts else "(No response received)"


# ── Chat handler ──────────────────────────────────────────────────────────────
# Gradio 6.12 Chatbot uses MessageDict format: {"role": "user"|"assistant", "content": str}

async def respond(message: str, history: list) -> tuple[list, str]:
    if not message.strip():
        return history, ""
    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": "..."},
    ]
    try:
        reply = await _call_agent(message)
    except Exception as e:
        reply = f"[Error] {e}"
    history[-1]["content"] = reply
    return history, ""


# ── Quick commands ────────────────────────────────────────────────────────────

QUICK_COMMANDS = [
    ("Help",          "help"),
    ("Daily Brief",   "daily brief"),
    ("Job Boards",    "check job boards"),
    ("Company Pages", "check company pages"),
    ("GitHub Trends", "what's trending on github"),
    ("My Profile",    "show my profile"),
    ("Usage",         "show usage"),
    ("Audit Repo",    "audit "),
]

RESUME_PROMPT_PREFIX = "tailor my resume for this job: "

_DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "application_drafts")


def _draft_files() -> list[str]:
    if not os.path.isdir(_DRAFTS_DIR):
        return []
    return sorted(
        [f for f in os.listdir(_DRAFTS_DIR) if f.endswith(".txt")],
        reverse=True,
    )


def _load_draft(filename: str) -> str:
    if not filename:
        return ""
    path = os.path.join(_DRAFTS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[File not found: {filename}]"


def _refresh_drafts() -> tuple[gr.Dropdown, str]:
    files = _draft_files()
    newest = files[0] if files else None
    content = _load_draft(newest) if newest else "No drafts saved yet."
    return gr.Dropdown(choices=files, value=newest), content


def _delete_draft(filename: str) -> tuple[gr.Dropdown, str]:
    if filename:
        path = os.path.join(_DRAFTS_DIR, filename)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    files = _draft_files()
    newest = files[0] if files else None
    content = _load_draft(newest) if newest else "No drafts saved yet."
    return gr.Dropdown(choices=files, value=newest), content


# ── ATS Scanner ───────────────────────────────────────────────────────────────

_ATS_SYSTEM_PROMPT = """
You are a thorough ATS (Applicant Tracking System) and hiring manager analyser.
Given a resume and a job description, return ONLY a valid JSON object.
No markdown fences, no preamble, no trailing commentary — raw JSON only.

The JSON must have exactly these keys:

match_score       — integer 0-100. Weight: 40% keywords, 25% experience/qualifications,
                    20% bullet quality, 15% structure.

verdict           — string. One sentence summarising the overall fit honestly.

keywords_found    — list of strings. Exact keywords/phrases from the job posting
                    that appear on the resume.

keywords_missing  — list of strings. Exact keywords/phrases from the job posting
                    completely absent from the resume.

keywords_partial  — list of strings. Keywords present but not prominent — mentioned
                    once, buried in a paragraph, or absent from skills/summary sections.

structural_issues — list of strings. Resume format/structure problems such as:
                    missing skills section, no measurable results in bullets,
                    inconsistent dates, absent summary, poor section ordering.

experience_gap    — string. One sentence comparing what the job requires (years,
                    level) vs. what the resume shows.
                    Example: "Role requires 3+ years; resume shows ~1 year via
                    academic projects and one internship."

seniority_fit     — string. Exactly one of these labels followed by a brief reason:
                    "Strong match", "Slight under-qualification",
                    "Significant under-qualification", "Over-qualified".
                    Example: "Slight under-qualification — role targets mid-level
                    but candidate is entry-level with strong project experience."

dealbreakers      — list of strings. Must-have requirements from the job posting
                    that are completely missing from the resume and would likely
                    cause automatic rejection. Be specific — quote the requirement.
                    Empty list if none.
                    Example: ["AWS required — no cloud experience on resume",
                               "3+ years Python — candidate shows ~1 year"]

qualification_gaps — list of strings. Specific gaps beyond keywords: certifications,
                    tools, methodologies, domain knowledge. State the gap and why
                    it matters.
                    Example: ["No CI/CD pipeline experience — job lists GitHub
                    Actions as required", "No mention of Agile/Scrum — team uses
                    sprint-based delivery"]

weak_bullets      — list of strings. 2-4 specific resume bullets that are vague or
                    lack measurable outcomes. Quote the bullet then note what is weak.
                    Example: ["'Worked on frontend features' — no metric, no outcome,
                    too vague", "'Helped with database design' — passive verb,
                    no result stated"]

top_recommendation — string. The single most impactful change to make right now.
                     One actionable sentence.
"""


def _ats_score_color(score: int) -> str:
    if score >= 80:
        return "#16a34a"   # green
    if score >= 60:
        return "#d97706"   # amber
    return "#dc2626"       # red


def _seniority_color(label: str) -> str:
    if label.startswith("Strong"):
        return "#16a34a"
    if label.startswith("Slight"):
        return "#d97706"
    return "#dc2626"


def _render_ats_results(data: dict) -> str:
    score        = int(data.get("match_score", 0))
    color        = _ats_score_color(score)
    verdict      = data.get("verdict", "")
    found        = data.get("keywords_found", [])
    missing      = data.get("keywords_missing", [])
    partial      = data.get("keywords_partial", [])
    issues       = data.get("structural_issues", [])
    rec          = data.get("top_recommendation", "")
    exp_gap      = data.get("experience_gap", "")
    seniority    = data.get("seniority_fit", "")
    dealbreakers = data.get("dealbreakers", [])
    qual_gaps    = data.get("qualification_gaps", [])
    weak_bullets = data.get("weak_bullets", [])

    def badges(items: list, cls: str) -> str:
        return " ".join(
            f'<span class="ats-badge {cls}" style="display:inline-block;'
            f'padding:2px 10px;border-radius:12px;font-size:.8rem;margin:2px;">'
            f'{item}</span>'
            for item in items
        )

    def ul(items: list, color: str = "#1a202c") -> str:
        return (
            "<ul style='margin:4px 0 0 18px;padding:0;'>"
            + "".join(
                f"<li style='font-size:.87rem;margin:3px 0;color:{color};'>{i}</li>"
                for i in items
            )
            + "</ul>"
        ) if items else f"<span style='font-size:.82rem;color:#64748b;'>None</span>"

    sen_color = _seniority_color(seniority) if seniority else "#64748b"

    dealbreaker_block = ""
    if dealbreakers:
        dealbreaker_block = f"""
  <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#dc2626;">⚠ Dealbreakers (auto-rejection risk)</strong>
    {ul(dealbreakers, "#991b1b")}
  </div>"""

    return f"""
<div style="font-family:'Segoe UI',system-ui,sans-serif;padding:16px;">

  <!-- Score gauge + verdict -->
  <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;">
    <div style="width:80px;height:80px;border-radius:50%;border:5px solid {color};
                display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span style="font-size:1.5rem;font-weight:700;color:{color};">{score}</span>
    </div>
    <div>
      <div style="height:14px;background:#e2e8f0;border-radius:7px;width:260px;overflow:hidden;">
        <div style="height:100%;width:{score}%;background:{color};border-radius:7px;"></div>
      </div>
      <p style="margin:8px 0 0;font-size:.95rem;color:#1a202c;">{verdict}</p>
    </div>
  </div>

  <!-- Experience + seniority row -->
  <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
    {"<div style='flex:1;min-width:200px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;'>"
     + "<strong style='font-size:.8rem;color:#475569;'>EXPERIENCE GAP</strong>"
     + f"<p style='margin:4px 0 0;font-size:.87rem;color:#1a202c;'>{exp_gap}</p></div>"
     if exp_gap else ""}
    {"<div style='flex:1;min-width:200px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px;'>"
     + "<strong style='font-size:.8rem;color:#475569;'>SENIORITY FIT</strong>"
     + f"<p style='margin:4px 0 0;font-size:.87rem;font-weight:600;color:{sen_color};'>{seniority}</p></div>"
     if seniority else ""}
  </div>

  <!-- Dealbreakers (shown only if present) -->
  {dealbreaker_block}

  <!-- Keywords -->
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#16a34a;">Keywords Found</strong><br>
    {badges(found, "ats-hit") if found else "<span style='font-size:.82rem;color:#64748b;'>None</span>"}
  </div>
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#dc2626;">Keywords Missing</strong><br>
    {badges(missing, "ats-miss") if missing else "<span style='font-size:.82rem;color:#64748b;'>None</span>"}
  </div>
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#d97706;">Keywords Partial</strong><br>
    {badges(partial, "ats-partial") if partial else "<span style='font-size:.82rem;color:#64748b;'>None</span>"}
  </div>

  <!-- Qualification gaps -->
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#9333ea;">Qualification Gaps</strong>
    {ul(qual_gaps, "#6b21a8")}
  </div>

  <!-- Structural issues -->
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#1a202c;">Structural Issues</strong>
    {ul(issues)}
  </div>

  <!-- Weak bullets -->
  <div style="margin-bottom:12px;">
    <strong style="font-size:.85rem;color:#b45309;">Weak Bullets to Rewrite</strong>
    {ul(weak_bullets, "#92400e")}
  </div>

  <!-- Top recommendation -->
  <div style="background:#f0f4ff;border:1px solid #c7d7f8;border-radius:8px;padding:12px;margin-top:8px;">
    <strong style="font-size:.85rem;color:#3b82f6;">Top Recommendation</strong>
    <p style="margin:6px 0 0;font-size:.9rem;color:#1a202c;">{rec}</p>
  </div>

</div>
"""


async def run_ats_scan(resume_text: str, job_text: str) -> str:
    if not resume_text.strip() or not job_text.strip():
        return '<p style="color:#dc2626;padding:12px;">Please paste both your resume and the job posting.</p>'

    try:
        import google.genai as genai
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", ""))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"RESUME:\n{resume_text}\n\nJOB POSTING:\n{job_text}",
            config=genai_types.GenerateContentConfig(
                system_instruction=_ATS_SYSTEM_PROMPT,
            ),
        )
        raw = response.text.strip()
        # Strip markdown fences if model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw.strip())
        return _render_ats_results(data)
    except json.JSONDecodeError:
        return (
            f'<p style="color:#dc2626;padding:12px;">Could not parse JSON response.</p>'
            f'<pre style="font-size:.8rem;white-space:pre-wrap;padding:12px;">{raw}</pre>'
        )
    except Exception as e:
        return f'<p style="color:#dc2626;padding:12px;">[ATS Error] {e}</p>'


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
/* ── Light mode (flat values, no CSS vars) ── */
body, .gradio-container {
    background: #f5f7fa !important;
    color: #1a202c !important;
    font-family: 'Segoe UI', system-ui, sans-serif !important;
}
#ds-header {
    background: #1e293b;
    color: #f8fafc !important;
    padding: 14px 20px;
    border-radius: 10px 10px 0 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
#ds-title { font-size:1.15rem; font-weight:700; color:#f8fafc !important; }
#ds-sub   { font-size:.75rem; opacity:.75; margin-top:2px; color:#cbd5e1 !important; }
#theme-btn {
    background: #334155 !important;
    color: #f8fafc !important;
    border: none !important;
    border-radius: 16px !important;
    padding: 6px 16px !important;
    font-size: .82rem !important;
    cursor: pointer !important;
}
#theme-btn:hover { opacity:.8 !important; }
#ds-status {
    background: #eef1f6;
    border: 1px solid #dde3ec;
    border-bottom: none;
    padding: 5px 16px;
    font-size: .73rem;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 6px;
}
.dot {
    width:7px; height:7px; border-radius:50%;
    background:#22c55e;
    animation: pulse 2s infinite;
    display:inline-block;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
#ds-quick {
    background: #eef1f6;
    border: 1px solid #dde3ec;
    border-bottom: none;
    padding: 8px 14px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.qbtn button {
    background: #ffffff !important;
    color: #3b82f6 !important;
    border: 1px solid #dde3ec !important;
    border-radius: 14px !important;
    padding: 3px 12px !important;
    font-size: .78rem !important;
    cursor: pointer !important;
}
.qbtn button:hover { background: #3b82f6 !important; color: #fff !important; }
#chatbox {
    background: #ffffff !important;
    border: 1px solid #dde3ec !important;
    border-top: none !important;
    border-radius: 0 !important;
}
#chatbox .user, #chatbox .message.user,
#chatbox [data-testid="user"] .bubble-wrap,
#chatbox .bubble-wrap.user {
    background: #3b82f6 !important;
    color: #ffffff !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 9px 14px !important;
    margin-left: auto !important;
    max-width: 78% !important;
}
#chatbox .bot, #chatbox .message.bot,
#chatbox [data-testid="bot"] .bubble-wrap,
#chatbox .bubble-wrap.bot {
    background: #eef1f6 !important;
    color: #1a202c !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 9px 14px !important;
    max-width: 85% !important;
    white-space: pre-wrap !important;
    font-family: 'Consolas','Courier New',monospace !important;
    font-size: .84rem !important;
    line-height: 1.55 !important;
}
/* Cascade text colour into every child element inside a bot bubble */
#chatbox .bot *, #chatbox .message.bot *,
#chatbox [data-testid="bot"] .bubble-wrap *,
#chatbox .bubble-wrap.bot * {
    color: #1a202c !important;
}
#chatbox .bot a, #chatbox .message.bot a,
#chatbox [data-testid="bot"] a, #chatbox .bubble-wrap.bot a {
    color: #2563eb !important;
}
#chatbox .bot code, #chatbox .message.bot code,
#chatbox [data-testid="bot"] code, #chatbox .bubble-wrap.bot code {
    background: #dde6f5 !important; color: #1e3a5f !important;
    border-radius: 3px !important; padding: 1px 5px !important;
}
#chatbox .bot pre, #chatbox .message.bot pre,
#chatbox [data-testid="bot"] pre, #chatbox .bubble-wrap.bot pre {
    background: #dde6f5 !important; border: 1px solid #c7d7f8 !important;
    border-radius: 6px !important; padding: 8px 12px !important;
}
#ds-input-row {
    background: #ffffff !important;
    border: 1px solid #dde3ec !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    padding: 10px 14px !important;
    gap: 8px !important;
}
#ds-textbox textarea {
    background: #ffffff !important;
    color: #1a202c !important;
    border: 1px solid #dde3ec !important;
    border-radius: 8px !important;
    padding: 9px 12px !important;
    font-size: .9rem !important;
}
#ds-textbox textarea:focus { border-color: #3b82f6 !important; outline: none !important; }
#ds-send {
    background: #3b82f6 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 42px !important;
    min-width: 72px !important;
}
#ds-send:hover { background: #2563eb !important; }
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-thumb { background: #dde3ec; border-radius:3px; }
#resume-panel {
    background: #f0f4ff;
    border: 1px solid #c7d7f8;
    border-top: none;
    border-radius: 0;
    padding: 10px 14px;
}
#resume-panel .label-wrap { display:none !important; }
#resume-job-input textarea {
    background: #ffffff !important;
    color: #1a202c !important;
    border: 1px solid #c7d7f8 !important;
    border-radius: 8px !important;
    padding: 9px 12px !important;
    font-size: .88rem !important;
}
#resume-job-input textarea:focus { border-color: #3b82f6 !important; outline: none !important; }
#resume-gen-btn {
    background: #7c3aed !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 42px !important;
}
#resume-gen-btn:hover { background: #6d28d9 !important; }
#drafts-btn {
    background: #0f766e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 42px !important;
    margin-top: 6px !important;
}
#drafts-btn:hover { background: #0d6460 !important; }
#resume-panel-label {
    font-size: .78rem;
    font-weight: 600;
    color: #7c3aed;
    letter-spacing: .03em;
    margin-bottom: 6px;
}
#drafts-viewer-panel {
    background: #f0fdf9;
    border: 1px solid #99f6e4;
    border-top: none;
    padding: 10px 14px 14px;
    border-radius: 0 0 10px 10px;
}
#drafts-viewer-label {
    font-size: .78rem;
    font-weight: 600;
    color: #0f766e;
    letter-spacing: .03em;
    margin-bottom: 6px;
}
#drafts-dropdown { margin-bottom: 6px; }
#drafts-dropdown .wrap,
#drafts-dropdown .wrap-inner,
#drafts-dropdown input,
#drafts-dropdown select { border-color: #99f6e4 !important; color: #1a202c !important; background: #ffffff !important; }
#drafts-dropdown .options,
#drafts-dropdown ul,
#drafts-dropdown [role="listbox"] { background: #ffffff !important; border: 1px solid #99f6e4 !important; }
#drafts-dropdown .item,
#drafts-dropdown li,
#drafts-dropdown option,
#drafts-dropdown [role="option"] { color: #1a202c !important; background: #ffffff !important; }
#drafts-dropdown .item:hover,
#drafts-dropdown [role="option"]:hover { background: #f0fdf9 !important; }
#drafts-content textarea {
    background: #ffffff !important;
    color: #1a202c !important;
    border: 1px solid #99f6e4 !important;
    border-radius: 8px !important;
    font-family: 'Consolas','Courier New',monospace !important;
    font-size: .82rem !important;
    line-height: 1.55 !important;
}
#refresh-btn {
    background: #0f766e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 36px !important;
}
#refresh-btn:hover { background: #0d6460 !important; }
#delete-draft-btn {
    background: #dc2626 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 36px !important;
}
#delete-draft-btn:hover { background: #b91c1c !important; }

/* ── ATS Scanner tab ── */
#ats-resume-input textarea,
#ats-job-input textarea {
    background: #ffffff !important;
    color: #1a202c !important;
    border: 1px solid #dde3ec !important;
    border-radius: 8px !important;
    font-family: 'Consolas','Courier New',monospace !important;
    font-size: .82rem !important;
    line-height: 1.55 !important;
    padding: 9px 12px !important;
}
#ats-resume-input textarea:focus,
#ats-job-input textarea:focus { border-color: #3b82f6 !important; outline: none !important; }
#ats-scan-btn {
    background: #7c3aed !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: 44px !important;
}
#ats-scan-btn:hover { background: #6d28d9 !important; }
#ats-results {
    background: #ffffff;
    border: 1px solid #dde3ec;
    border-radius: 8px;
    min-height: 80px;
}
.ats-badge.ats-hit     { background: #dcfce7; color: #166534; }
.ats-badge.ats-miss    { background: #fee2e2; color: #991b1b; }
.ats-badge.ats-partial { background: #fef9c3; color: #854d0e; }
"""

JS_TOGGLE = """
const DARK_CSS = `
  body, .gradio-container, .main, footer { background: #0f172a !important; color: #f1f5f9 !important; }
  #ds-header  { background: #020817 !important; }
  #ds-status  { background: #1e293b !important; border-color: #334155 !important; color: #94a3b8 !important; }
  #ds-quick   { background: #1e293b !important; border-color: #334155 !important; }
  .qbtn button { background: #253347 !important; color: #60a5fa !important; border-color: #334155 !important; }
  .qbtn button:hover { background: #3b82f6 !important; color: #fff !important; }
  #chatbox, #chatbox > div { background: #1e293b !important; border-color: #334155 !important; }

  /* ── Bot bubble: background + every child element ── */
  #chatbox .bot, #chatbox .message.bot,
  #chatbox [data-testid="bot"] .bubble-wrap,
  #chatbox .bubble-wrap.bot {
    background: #253347 !important;
    color: #f1f5f9 !important;
  }
  #chatbox .bot *, #chatbox .message.bot *,
  #chatbox [data-testid="bot"] .bubble-wrap *,
  #chatbox .bubble-wrap.bot *,
  #chatbox [data-testid="bot"] p,
  #chatbox [data-testid="bot"] span,
  #chatbox [data-testid="bot"] li,
  #chatbox [data-testid="bot"] strong,
  #chatbox [data-testid="bot"] em,
  #chatbox [data-testid="bot"] h1,
  #chatbox [data-testid="bot"] h2,
  #chatbox [data-testid="bot"] h3,
  #chatbox [data-testid="bot"] td,
  #chatbox [data-testid="bot"] th { color: #f1f5f9 !important; }

  /* ── Links in chat ── */
  #chatbox a, #chatbox .bot a,
  #chatbox [data-testid="bot"] a { color: #60a5fa !important; }

  /* ── Inline code in bot bubbles ── */
  #chatbox .bot code, #chatbox .message.bot code,
  #chatbox [data-testid="bot"] code, #chatbox .bubble-wrap.bot code {
    background: #0d1b2e !important;
    color: #93c5fd !important;
    border: 1px solid #334155 !important;
    border-radius: 3px !important;
    padding: 1px 5px !important;
  }
  /* ── Code blocks (pre) in bot bubbles ── */
  #chatbox .bot pre, #chatbox .message.bot pre,
  #chatbox [data-testid="bot"] pre, #chatbox .bubble-wrap.bot pre {
    background: #0d1b2e !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    color: #e2e8f0 !important;
  }
  #chatbox .bot pre *, #chatbox [data-testid="bot"] pre * { color: #e2e8f0 !important; }

  /* ── User bubble stays white ── */
  #chatbox .user, #chatbox [data-testid="user"] .bubble-wrap { background: #2563eb !important; }
  #chatbox .user *, #chatbox [data-testid="user"] * { color: #ffffff !important; }

  #ds-input-row  { background: #1e293b !important; border-color: #334155 !important; }
  #ds-textbox textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  #resume-panel  { background: #1a1f35 !important; border-color: #334155 !important; }
  #resume-panel-label { color: #a78bfa !important; }
  #resume-job-input textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  #drafts-btn { background: #0f766e !important; color: #fff !important; }
  #drafts-viewer-panel { background: #0d1f1e !important; border-color: #134e4a !important; }
  #drafts-viewer-label { color: #2dd4bf !important; }
  /* ── Drafts dropdown: every part ── */
  #drafts-dropdown .wrap,
  #drafts-dropdown .wrap-inner,
  #drafts-dropdown input,
  #drafts-dropdown select { background: #0f172a !important; color: #f1f5f9 !important; border-color: #134e4a !important; }
  #drafts-dropdown * { color: #f1f5f9 !important; }
  #drafts-dropdown .options,
  #drafts-dropdown ul,
  #drafts-dropdown [role="listbox"] { background: #1e293b !important; border: 1px solid #134e4a !important; }
  #drafts-dropdown .item,
  #drafts-dropdown li,
  #drafts-dropdown option,
  #drafts-dropdown [role="option"] { background: #1e293b !important; color: #f1f5f9 !important; }
  #drafts-dropdown .item:hover,
  #drafts-dropdown li:hover,
  #drafts-dropdown [role="option"]:hover,
  #drafts-dropdown .item.selected { background: #134e4a !important; color: #f1f5f9 !important; }
  #drafts-content textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #134e4a !important; }
  #refresh-btn { background: #0f766e !important; }
  #delete-draft-btn { background: #dc2626 !important; color: #fff !important; }
  #theme-btn { background: #475569 !important; }
  .message-wrap, .wrap { background: #1e293b !important; }
  ::-webkit-scrollbar-thumb { background: #475569 !important; }

  /* ── Tab navigation — dark mode ── */
  .tab-nav, .tabs .tab-nav {
    background: #1e293b !important;
    border-color: #334155 !important;
  }
  .tab-nav button, .tabs .tab-nav button, button[role="tab"] {
    color: #94a3b8 !important;
    background: transparent !important;
    border-color: transparent !important;
  }
  .tab-nav button.selected,
  .tabs .tab-nav button.selected,
  button[role="tab"][aria-selected="true"] {
    color: #f1f5f9 !important;
    background: #0f172a !important;
    border-bottom-color: #3b82f6 !important;
    font-weight: 700 !important;
  }
  .tab-nav button:hover, button[role="tab"]:hover {
    color: #e2e8f0 !important;
    background: #253347 !important;
  }

  /* ── ATS Scanner tab — dark mode ── */
  #ats-resume-input textarea,
  #ats-job-input textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  #ats-results { background: #1e293b !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  .ats-badge.ats-hit     { background: #14532d !important; color: #bbf7d0 !important; }
  .ats-badge.ats-miss    { background: #7f1d1d !important; color: #fecaca !important; }
  .ats-badge.ats-partial { background: #713f12 !important; color: #fef08a !important; }
`;

function applyDark() {
    if (!document.getElementById('ds-dark-style')) {
        const s = document.createElement('style');
        s.id = 'ds-dark-style';
        s.textContent = DARK_CSS;
        document.head.appendChild(s);
    }
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = 'Light Mode';
    localStorage.setItem('ds-theme', 'dark');
}

function applyLight() {
    const s = document.getElementById('ds-dark-style');
    if (s) s.remove();
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = 'Dark Mode';
    localStorage.setItem('ds-theme', 'light');
}

function toggleTheme() {
    if (document.getElementById('ds-dark-style')) { applyLight(); }
    else { applyDark(); }
}

// Restore saved preference on every page load
(function restore() {
    if (!document.head) { setTimeout(restore, 50); return; }
    if (localStorage.getItem('ds-theme') === 'dark') applyDark();
})();
"""

# ── Build UI ──────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Digital Sentinel") as demo:

        # Header (outside tabs — always visible)
        gr.HTML("""
        <div id="ds-header">
            <div>
                <div id="ds-title">Digital Sentinel</div>
                <div id="ds-sub">Personal Security &amp; Career Orchestrator &nbsp;·&nbsp; Gemini 2.5 Flash</div>
            </div>
            <button id="theme-btn" onclick="toggleTheme()">Dark Mode</button>
        </div>
        """)

        with gr.Tabs():

            # ── Tab 1: Chat ───────────────────────────────────────────────────
            with gr.Tab("Chat"):

                # Status bar
                gr.HTML("""
                <div id="ds-status">
                    <span class="dot"></span>
                    Running locally &nbsp;·&nbsp; Google ADK 1.29 &nbsp;·&nbsp; All agents ready
                </div>
                """)

                # Quick command buttons
                quick_btns: list[gr.Button] = []
                with gr.Row(elem_id="ds-quick"):
                    for label, _ in QUICK_COMMANDS:
                        b = gr.Button(label, elem_classes=["qbtn"], size="sm")
                        quick_btns.append(b)

                # Chatbot
                chatbot = gr.Chatbot(
                    value=[],
                    elem_id="chatbox",
                    show_label=False,
                    height=460,
                )

                # Input row
                with gr.Row(elem_id="ds-input-row"):
                    msg_box = gr.Textbox(
                        placeholder='Type a message and press Enter — or say "help" to start',
                        show_label=False,
                        lines=1,
                        max_lines=5,
                        elem_id="ds-textbox",
                        scale=9,
                        autofocus=True,
                    )
                    send_btn = gr.Button("Send", elem_id="ds-send", scale=1, variant="primary")

                # Resume & Cover Letter panel
                with gr.Row(elem_id="resume-panel"):
                    with gr.Column(scale=9):
                        gr.HTML('<div id="resume-panel-label">Resume &amp; Cover Letter Generator — paste a job URL or description below</div>')
                        resume_job_input = gr.Textbox(
                            placeholder="https://example.com/job/123  — or paste the full job description here",
                            show_label=False,
                            lines=2,
                            max_lines=8,
                            elem_id="resume-job-input",
                        )
                    with gr.Column(scale=1, min_width=190):
                        resume_gen_btn = gr.Button(
                            "Generate Resume & Cover Letter",
                            elem_id="resume-gen-btn",
                            variant="primary",
                        )
                        drafts_btn = gr.Button(
                            "View Saved Drafts",
                            elem_id="drafts-btn",
                            variant="secondary",
                        )

                # Saved Drafts viewer panel
                initial_files = _draft_files()
                initial_newest = initial_files[0] if initial_files else None
                with gr.Row(elem_id="drafts-viewer-panel"):
                    with gr.Column():
                        gr.HTML('<div id="drafts-viewer-label">Saved Application Drafts</div>')
                        with gr.Row():
                            drafts_dropdown = gr.Dropdown(
                                choices=initial_files,
                                value=initial_newest,
                                show_label=False,
                                elem_id="drafts-dropdown",
                                scale=9,
                            )
                            refresh_btn = gr.Button(
                                "Refresh",
                                elem_id="refresh-btn",
                                scale=1,
                                min_width=80,
                            )
                            delete_draft_btn = gr.Button(
                                "Delete",
                                elem_id="delete-draft-btn",
                                scale=1,
                                min_width=80,
                            )
                        drafts_content = gr.Textbox(
                            value=_load_draft(initial_newest) if initial_newest else "No drafts saved yet.",
                            show_label=False,
                            lines=14,
                            max_lines=30,
                            interactive=False,
                            elem_id="drafts-content",
                        )

            # ── Tab 2: ATS Scanner ────────────────────────────────────────────
            with gr.Tab("ATS Scanner"):

                with gr.Row():
                    with gr.Column():
                        resume_input = gr.Textbox(
                            label="Your Resume",
                            lines=20,
                            placeholder="Paste your resume text here...",
                            elem_id="ats-resume-input",
                        )
                    with gr.Column():
                        job_input = gr.Textbox(
                            label="Job Posting",
                            lines=20,
                            placeholder="Paste the job description here...",
                            elem_id="ats-job-input",
                        )

                ats_scan_btn = gr.Button(
                    "Scan with ATS Analyzer",
                    elem_id="ats-scan-btn",
                    variant="primary",
                )

                ats_results = gr.HTML(
                    value="",
                    elem_id="ats-results",
                )

        # ── Wire events ───────────────────────────────────────────────────────

        msg_box.submit(respond, [msg_box, chatbot], [chatbot, msg_box])
        send_btn.click(respond, [msg_box, chatbot], [chatbot, msg_box])

        # Quick buttons: fill textbox then submit
        for btn, (_, cmd) in zip(quick_btns, QUICK_COMMANDS):
            btn.click(fn=lambda c=cmd: c, outputs=msg_box).then(
                respond, [msg_box, chatbot], [chatbot, msg_box]
            )

        # Resume generator button: build prompt from job input, send to agent
        def _build_resume_prompt(job_text: str) -> tuple[str, str]:
            job_text = job_text.strip()
            if not job_text:
                return "", ""
            prompt = f"{RESUME_PROMPT_PREFIX}{job_text}"
            return prompt, ""

        resume_gen_btn.click(
            fn=_build_resume_prompt,
            inputs=[resume_job_input],
            outputs=[msg_box, resume_job_input],
        ).then(
            respond, [msg_box, chatbot], [chatbot, msg_box]
        )

        drafts_btn.click(
            fn=lambda: "show my drafts",
            outputs=msg_box,
        ).then(
            respond, [msg_box, chatbot], [chatbot, msg_box]
        )

        # Drafts viewer: selecting a draft loads its content
        drafts_dropdown.change(
            fn=_load_draft,
            inputs=[drafts_dropdown],
            outputs=[drafts_content],
        )

        # Refresh: re-scan the folder and pick the newest draft
        refresh_btn.click(
            fn=_refresh_drafts,
            outputs=[drafts_dropdown, drafts_content],
        )

        # Delete: remove selected file, reload dropdown to next available draft
        delete_draft_btn.click(
            fn=_delete_draft,
            inputs=[drafts_dropdown],
            outputs=[drafts_dropdown, drafts_content],
        )

        # ATS Scanner: run scan on button click
        ats_scan_btn.click(
            fn=run_ats_scan,
            inputs=[resume_input, job_input],
            outputs=[ats_results],
        )

    return demo


if __name__ == "__main__":
    print()
    print("  ==========================================")
    print("   DIGITAL SENTINEL")
    print("   Personal Security & Career Orchestrator")
    print("  ==========================================")
    print()
    import socket
    local_ip = socket.gethostbyname(socket.gethostname())
    print("  URL (this PC) : http://127.0.0.1:7860")
    print(f"  URL (phone)   : http://{local_ip}:7860  ← open on any device on same WiFi")
    print("  Stop: Ctrl+C")
    print()
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        inbrowser=True,
        quiet=True,
        css=CSS,
        js=JS_TOGGLE,
        theme=gr.themes.Base(),
    )
