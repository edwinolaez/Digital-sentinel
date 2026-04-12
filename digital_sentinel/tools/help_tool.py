"""
Digital Sentinel — Help Tool
Returns a formatted command reference card when the user asks for help.
"""


def get_help() -> str:
    """Returns the full Digital Sentinel command reference card.

    Call this when the user says 'help', 'commands', 'what can you do',
    or starts the session and wants to know what's available.

    Returns:
        A formatted reference card listing all available commands grouped by mission.
    """
    return """
╔══════════════════════════════════════════════════════════╗
║           DIGITAL SENTINEL — COMMAND REFERENCE           ║
║         Personal Security & Career Orchestrator          ║
╚══════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  daily brief              Full morning report: emails + job boards
                           + career page changes + top 3 trends
  help                     Show this reference card
  show usage               Token usage + estimated cost breakdown
                           by agent, by day, and all-time total

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 1 — EMAIL & CAREER SCOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  check my gmail           Fetch unread Gmail headers
  check my yahoo           Fetch unread Yahoo headers
  scan my emails           Fetch both inboxes + run career scout
  scan my emails for job leads
                           Filter for entry-level software roles

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 2 — CLONE GUARD (GitHub Safety)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  audit https://github.com/owner/repo
                           Security check before cloning/forking
                           Returns: SAFE / CAUTION / DANGEROUS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 3 — GITHUB TREND INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  what's trending on github
  what's hot in AI this week
  github trends last 30 days
  what should I learn next  AI-powered trend report with career
                            recommendations for your stack

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 4 — JOB HUNTING (Beyond LinkedIn)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  check job boards         Live postings from RemoteOK + Arbeitnow
                           (scam-filtered, scored MATCH / REVIEW)

  check company pages      Scan 12 Calgary/Canadian tech company
                           career pages for new postings since last check

  which companies are you watching
                           List all monitored company career pages

  log I applied to [Company] for [Role]
  log application [Company] | [Role] | [URL]
                           Track a new application

  show my applications     Full application list
  show active applications Filter by status
  any follow-ups needed?   Flag applications silent for 14+ days

  update application #3 status to interview
  [Company] rejected me    Update status on an existing application

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 5 — PROFILE MANAGER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  show my profile          View your full profile
  edit my profile          Open profile editing mode
  update my LinkedIn to [url]
  update my GitHub to [url]
  add [skill] to my skills
  remove [skill] from my skills
  add a new project        Add project interactively
  update project [name]    Edit an existing project's details
  remove project [name]    Remove a project
  add [company] to my target companies
  set my career goal to [goal]
  add interest: [topic]    Add to technical or personal interests
  set my salary expectation to [range]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 6 — COLD OUTREACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  draft a cold email to a [role] at [Company]
  draft a LinkedIn message to the hiring manager at [Company]
  write an outreach message for a React role at [Company]
                           Personalized cold outreach using your
                           real background and projects

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MISSION 6 — RESUME COACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  tailor my resume for [URL]
  tailor my resume for this job: [paste description]
                           Full analysis: ATS keywords, requirement
                           coverage map, bullet rewrites, project selection

  what keywords am I missing for this role: [text]
  which of my projects fits this posting: [text]
  write me a cover letter for this job: [URL or text]
  how do I match up against this posting: [text]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SECURITY — built into every workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  All job postings    → scam content scan (auto)
  All job URLs        → domain safety check (auto)
  All email subjects  → phishing / scam detection (auto)
  All GitHub repos    → Clone Guard audit on request
  Trend repo picks    → top 3 auto-audited before recommendation

══════════════════════════════════════════════════════════
  Stack: Python 3.13 · Google ADK 1.29 · Gemini 2.5 Flash
  Run: adk web  from the digital-sentinel/ directory
══════════════════════════════════════════════════════════
"""
