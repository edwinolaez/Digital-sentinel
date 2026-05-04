# Digital Sentinel
### Personal Security & Career Orchestrator
**Google ADK 1.29 · Gemini 2.5 Flash · Python 3.13 · Gradio 6**

---

## What It Does

Digital Sentinel is a fully local, multi-agent AI assistant that runs on your machine and handles the routine grind of a job search — securely. It combines six missions into one conversational interface:

| Mission | What it does |
|---------|-------------|
| **Email & Career Scout** | Sweeps Gmail + Yahoo simultaneously for job leads, filters for entry-level software roles, flags phishing/scam subjects automatically |
| **Clone Guard** | Audits any GitHub repo for red flags before you clone or fork it — returns SAFE / CAUTION / DANGEROUS |
| **GitHub Trend Intelligence** | Fetches the fastest-rising repos across 8 tech categories, then uses Gemini to synthesise career-relevant learning recommendations |
| **Job Hunting** | Pulls live postings from RemoteOK + Arbeitnow, monitors 12 Calgary/Canadian company career pages for new listings, tracks every application you log |
| **Resume & Cover Letter Generator** | Dedicated dashboard panel — paste a job URL or description, get a full functional resume (Professional Summary → Highlights → Skills → PAR-format Experience bullets → Work History → Education) plus a 3-paragraph cover letter, auto-saved as a draft |
| **Cold Outreach** | Writes personalised cold emails + LinkedIn messages using your real background; 4-6 sentence max, specific, single ask |
| **Profile Manager** | Single source of truth for all agents — edit your skills, projects, goals, and preferences through natural conversation |

Every workflow runs a security layer: all job URLs are domain-checked, all posting text is scanned for scam signals, and all GitHub repos can be audited on demand.

---

## Architecture

```
digital-sentinel/
├── app.py                          ← Custom Gradio UI (replaces adk web)
├── launch.bat                      ← Terminal launcher (dev use)
├── launch.vbs                      ← Silent launcher for desktop shortcut
├── profile.json                    ← Your profile (auto-created, git-ignored)
├── safety_auditor.py               ← Standalone repo auditor
└── digital_sentinel/
    ├── agent.py                    ← All 7 agents defined here
    └── tools/
        ├── email_tool.py           ← Gmail (OAuth) · Yahoo (IMAP/SSL)
        ├── career_scout.py         ← Job filter + phishing detector on emails
        ├── trend_scout.py          ← GitHub trending repo fetcher (8 categories)
        ├── repo_auditor.py         ← ADK wrapper for Clone Guard
        ├── scam_detector.py        ← URL safety + scam content scanner
        ├── job_board_scout.py      ← RemoteOK + Arbeitnow live postings
        ├── career_page_monitor.py  ← 12 company career pages (hash comparison)
        ├── application_tracker.py  ← Log + track job applications
        ├── resume_tools.py         ← Job posting fetcher for resume coaching
        ├── application_drafter.py  ← Save cover letters + resume bullets as local drafts
        ├── profile_manager.py      ← Profile CRUD (7 functions)
        ├── usage_tracker.py        ← Token usage + cost estimation
        └── help_tool.py            ← Command reference card
```

### Agent Architecture

```
root_agent  (LlmAgent — orchestrator)
├── email_fan_out  (ParallelAgent)
│       ├── gmail_worker    → fetch_gmail_emails()
│       └── yahoo_worker    → fetch_yahoo_emails()
├── trend_analyst  (LlmAgent)
│       └── fetch_github_trending() · audit_github_repo()
├── career_hunter  (LlmAgent)
│       └── scout_job_boards() · monitor_career_pages()
│           log_application() · update_application_status()
│           get_applications() · flag_stale_applications()
│           check_url_safety() · scan_for_scam_signals()
├── outreach_agent (LlmAgent)
│       └── get_profile()
├── resume_coach   (LlmAgent)
│       └── get_profile() · fetch_job_posting() · save_application_draft() · list_saved_drafts() · create_gmail_draft()
└── profile_agent  (LlmAgent)
        └── get_profile() · set_profile_field() · add_to_list()
            remove_from_list() · add_project() · update_project()
            remove_project()
```

All agents share a `_track_usage` callback that records token counts to `usage_log.json` after every Gemini call.

---

## Setup

### Prerequisites
- Python 3.12+
- Virtual environment at `.sentinel_env/`
- Google ADK 1.29+

### 1. Activate the environment

```powershell
.sentinel_env\Scripts\activate
```

### 2. Configure `.env`

```env
# Gemini — get from https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_key_here
GOOGLE_GENAI_API_KEY=your_key_here

# Yahoo IMAP
YAHOO_USER=your_yahoo@yahoo.com
YAHOO_APP_PASSWORD=your_16_char_app_password

# GitHub read-only PAT
GITHUB_PAT=ghp_your_token_here
```

### 3. Gmail OAuth (first run only)

A browser tab opens asking you to grant Gmail read-only access. After approval `token.json` is saved — future runs are instant.

### 4. Run

```powershell
# From the digital-sentinel/ directory
python app.py
```

Opens automatically at **http://127.0.0.1:7860**

**Desktop shortcut** — double-click `Digital Sentinel` on your desktop. The server starts in a hidden window and your browser opens automatically. To stop it, open Task Manager and end the `python.exe` process.

---

## Command Reference

```
QUICK START
  daily brief           Full morning report: emails + job boards
                        + career page changes + top 3 trends
  help                  Show the full command reference card
  show usage            Token usage + estimated cost by agent / day / all-time

MISSION 1 — EMAIL & CAREER SCOUT
  check my gmail        Fetch unread Gmail headers
  check my yahoo        Fetch unread Yahoo headers
  scan my emails        Both inboxes + career scout
  scan my emails for job leads

MISSION 2 — CLONE GUARD
  audit https://github.com/owner/repo
                        Security check → SAFE / CAUTION / DANGEROUS

MISSION 3 — GITHUB TREND INTELLIGENCE
  what's trending on github
  what's hot in AI this week
  github trends last 30 days
  what should I learn next

MISSION 4 — JOB HUNTING
  check job boards      Live postings from RemoteOK + Arbeitnow
  check company pages   Scan 12 Calgary/Canadian company career pages
  which companies are you watching
  log I applied to [Company] for [Role]
  show my applications
  any follow-ups needed?
  update application #3 status to interview

MISSION 5 — PROFILE MANAGER
  show my profile
  update my LinkedIn to [url]
  add [skill] to my skills
  add a new project
  set my career goal to [goal]

MISSION 6 — RESUME & COVER LETTER GENERATOR
  [Dashboard panel] Paste a job URL or description into the purple
  "Resume & Cover Letter Generator" panel and click the button.
  The agent produces a full functional resume + cover letter and
  saves it to application_drafts/ automatically.

  tailor my resume for [URL or paste job description]
  write me a cover letter for this job: [URL or text]
  how do I match up against this posting: [text]
  show my drafts

MISSION 7 — COLD OUTREACH
  draft a cold email to a [role] at [Company]
  draft a LinkedIn message to the hiring manager at [Company]
```

---

## Security Model

| Surface | Protection |
|---------|-----------|
| Job board postings | Scam signal scan (auto) — SCAM posts dropped silently |
| Job URLs | Domain safety check (whitelist + TLD + typosquat detection) |
| Email subjects | Phishing / scam pattern detection (auto) |
| GitHub repos | Clone Guard audit on request; trend picks auto-audited |
| Resume job URLs | URL safety check before fetch — SUSPICIOUS domains blocked |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | Google ADK 1.29.0 |
| LLM | Gemini 2.5 Flash |
| UI | Gradio 6 (custom CSS + dark/light mode) |
| Email — Gmail | Gmail API + OAuth 2.0 |
| Email — Yahoo | IMAP over SSL |
| Job boards | RemoteOK API · Arbeitnow API |
| GitHub data | GitHub Search REST API |
| Secrets | `python-dotenv` |
| Language | Python 3.13 |

---

## Files Never Committed

```
.env                         — API keys and credentials
credentials.json             — Google OAuth client secret
token.json                   — Gmail OAuth token (auto-generated)
.sentinel_env/               — Virtual environment
profile.json                 — Personal profile data
usage_log.json               — Token usage log
applications.json            — Job application tracker
career_page_snapshots.json   — Career page hash cache
```

---

*Built April 2026 — SAIT Software Development Program*
