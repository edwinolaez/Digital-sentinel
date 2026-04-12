# Digital Sentinel — Build Progress

## Project Overview
Personal Security & Career Orchestrator built with Google ADK + Gemini 2.5 Flash.
Runs fully locally. No deployment required.

---

## Build Log

### Phase 1 — Core Agent + Email Scout
**Status: Complete**

- Set up Google ADK project structure (`digital_sentinel/` package)
- Configured `root_agent` using `LlmAgent` with Gemini 2.5 Flash
- Implemented `email_tool.py` — Gmail via OAuth 2.0, Yahoo via IMAP/SSL
- Implemented `career_scout.py` — filters email headers for entry-level software roles
- Implemented `ParallelAgent` fan-out (`email_fan_out`) so both inboxes fetch simultaneously
- `daily brief` command triggers full email + trend report in one pass

---

### Phase 2 — Clone Guard + GitHub Trend Intelligence
**Status: Complete**

- `repo_auditor.py` — wraps GitHub REST API; returns SAFE / CAUTION / DANGEROUS verdict
- `safety_auditor.py` — standalone auditor (used by both ADK agent and CLI)
- `trend_scout.py` — queries GitHub Search API across 8 tech categories:
  Python · TypeScript · JavaScript · React/Next.js · AI/LLM · Rust · Go · DevOps
- `trend_analyst` sub-agent applies Gemini reasoning to raw repo data:
  star velocity, recency, career relevance, learning recommendations
- Auto-audits top 3 trending repos before recommending them

---

### Phase 3 — Job Hunting Suite
**Status: Complete**

- `job_board_scout.py` — live postings from RemoteOK + Arbeitnow APIs
  - Scam filter: SCAM-rated posts dropped silently; CAUTION posts flagged inline
  - Posts scored MATCH / REVIEW based on role relevance
- `career_page_monitor.py` — SHA-256 hash comparison on 12 company career pages:
  Neo Financial · Bold Commerce · Benevity · Helcim · Jobber · ATB Financial ·
  Symend · Ownr · Showpass · Absorb LMS · Decisiv · Miovision
- `application_tracker.py` — `applications.json` persistence
  - `log_application` · `update_application_status` · `get_applications`
  - `flag_stale_applications(days=14)` — surfaces follow-up reminders
- `career_hunter` sub-agent orchestrates all job hunting tools

---

### Phase 4 — Scam & Security Layer
**Status: Complete**

- `scam_detector.py` — two-function security toolkit:
  - `check_url_safety(url)` — whitelist of 30+ safe domains, suspicious TLD check
    (.tk/.ml/.ga/.cf), typosquatting detection against known job sites
  - `scan_for_scam_signals(text)` — strong patterns (bitcoin, wire transfer,
    reshipping) → SCAM; 3+ soft patterns → CAUTION; clean → SAFE
- Wired into every workflow:
  - Job board postings — scanned automatically, SCAM posts silently dropped
  - Job URLs in resume coaching — safety check before fetch, SUSPICIOUS blocked
  - Email subjects — phishing patterns flagged in career scout report
  - GitHub repos — Clone Guard available on demand; trend picks auto-audited

---

### Phase 5 — Cold Outreach & Resume Coach
**Status: Complete**

- `outreach_agent` sub-agent — reads full profile via `get_profile()` before drafting
  - Cold emails, LinkedIn messages, role-specific outreach
  - All output grounded in Edwin's actual projects, stack, and background
- `resume_coach` sub-agent — job posting analysis pipeline:
  1. Fetch posting (`resume_tools.py` with URL safety check)
  2. Load profile (`get_profile()`)
  3. ATS keyword gap analysis
  4. Requirement coverage map (met / partially met / missing)
  5. Bullet rewrite suggestions
  6. Project selection recommendation
  7. Cover letter generation

---

### Phase 6 — Profile Manager
**Status: Complete**

- `profile.json` — single source of truth for all agents
  - Pre-populated: personal info, SAIT education, skills, 3 projects, goals, preferences
- `profile_manager.py` — 7 CRUD functions:
  - `get_profile()` · `set_profile_field(path, value)`
  - `add_to_list(path, item)` · `remove_from_list(path, item)`
  - `add_project(...)` · `update_project(...)` · `remove_project(name)`
- `profile_agent` sub-agent handles all profile edits through natural conversation
- All agents call `get_profile()` at task start — no hardcoded personal data anywhere

---

### Phase 7 — Token Usage Tracking
**Status: Complete**

- `usage_tracker.py` — `usage_log.json` persistence
  - Records per-agent token counts after every Gemini call via `after_model_callback`
  - Pricing applied: $0.075 / 1M input tokens · $0.30 / 1M output tokens (Gemini 2.5 Flash)
- `get_usage_report()` returns:
  - Today's usage by agent
  - Last 7 days totals
  - Per-agent all-time breakdown
  - Running cost estimate
- Accessible via `show usage` command in the chat

---

### Phase 8 — Help System
**Status: Complete**

- `help_tool.py` — `get_help()` returns full ASCII command reference card
- Covers all 6 missions with exact command syntax
- Accessible via `help` or `commands` in the chat

---

### Phase 9 — Custom Gradio UI
**Status: Complete**

- Replaced `adk web` with a custom `app.py` using Gradio 6 `gr.Blocks`
- Features:
  - Dark / light mode toggle — JS injected via `launch(js=...)`, persisted in `localStorage`
  - Quick command buttons bar — 8 one-click shortcuts
  - Animated status dot (live pulse)
  - Clean chat bubbles: user (blue, right-aligned) · bot (monospace, pre-wrap)
  - Custom scrollbar, autofocus input, Send button
- Resolved Gradio 6 breaking changes:
  - `css` / `theme` / `js` moved to `launch()` (not `Blocks()`)
  - Removed deprecated `type="messages"` and `show_api=False`
  - Quick buttons stored in a list during creation loop (not fragile block index)
  - Dark mode CSS injected as `<style>` tag — not CSS variables (Gradio overrides vars)

---

### Phase 10 — Desktop Launcher
**Status: Complete**

- `launch.bat` — activates `.sentinel_env`, runs `python app.py` (dev use)
- `launch.vbs` — VBScript wrapper that runs the server with window style `0` (hidden)
  Browser opens automatically via `inbrowser=True`; no terminal window visible
- Desktop shortcut: `wscript.exe "launch.vbs"` — double-click to launch, no setup

---

## Feature Status

| Feature | Status |
|---------|--------|
| Gmail fetching (OAuth 2.0) | Working |
| Yahoo fetching (IMAP/SSL) | Working |
| ParallelAgent inbox fan-out | Working |
| Career scout (email job filter) | Working |
| Clone Guard (repo audit) | Working |
| GitHub trend intelligence (8 categories) | Working |
| Job board scout (RemoteOK + Arbeitnow) | Working |
| Company career page monitor (12 companies) | Working |
| Application tracker | Working |
| Scam & URL security layer | Working |
| Cold outreach drafter | Working |
| Resume coach (posting analysis) | Working |
| Profile manager (CRUD) | Working |
| Token usage tracking | Working |
| Help command reference | Working |
| Custom Gradio UI | Working |
| Dark / light mode toggle | Working |
| Desktop shortcut (silent launch) | Working |

---

## Known Constraints

- **No deployment** — runs locally only; intentional (keeps credentials off the internet)
- **Career page monitor** — uses HTTP hash comparison, not JS rendering; pages that load postings via client-side JavaScript may not reflect changes
- **Gmail OAuth** — requires one-time browser sign-in on first run; `token.json` persists after that
- **To stop the server** — Task Manager → end `python.exe` (when launched via desktop shortcut)

---

## Stack Summary

| Layer | Technology |
|-------|-----------|
| Agent framework | Google ADK 1.29.0 |
| LLM | Gemini 2.5 Flash |
| UI | Gradio 6 (custom CSS + JS) |
| Email — Gmail | Gmail API + OAuth 2.0 |
| Email — Yahoo | IMAP over SSL |
| Job boards | RemoteOK API · Arbeitnow API |
| GitHub data | GitHub Search REST API |
| Secrets | python-dotenv |
| Language | Python 3.13 |

---

*Last updated: April 2026*
