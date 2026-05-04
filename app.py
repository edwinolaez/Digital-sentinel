"""
Digital Sentinel — Custom Gradio UI
Run with: python app.py  (from the digital-sentinel/ directory)
Serves at: http://127.0.0.1:7860
"""
import asyncio
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
#resume-panel-label {
    font-size: .78rem;
    font-weight: 600;
    color: #7c3aed;
    letter-spacing: .03em;
    margin-bottom: 6px;
}
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
  #chatbox .user { background: #2563eb !important; color: #fff !important; }
  #chatbox .bot  { background: #253347 !important; color: #f1f5f9 !important; }
  #ds-input-row  { background: #1e293b !important; border-color: #334155 !important; }
  #ds-textbox textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  #resume-panel  { background: #1a1f35 !important; border-color: #334155 !important; }
  #resume-panel-label { color: #a78bfa !important; }
  #resume-job-input textarea { background: #0f172a !important; color: #f1f5f9 !important; border-color: #334155 !important; }
  #theme-btn { background: #475569 !important; }
  .message-wrap, .wrap, .svelte-1ipelgc { background: #1e293b !important; }
  .prose, p, span, label, .label-wrap { color: #f1f5f9 !important; }
  ::-webkit-scrollbar-thumb { background: #475569 !important; }
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

        # Header
        gr.HTML("""
        <div id="ds-header">
            <div>
                <div id="ds-title">Digital Sentinel</div>
                <div id="ds-sub">Personal Security &amp; Career Orchestrator &nbsp;·&nbsp; Gemini 2.5 Flash</div>
            </div>
            <button id="theme-btn" onclick="toggleTheme()">Dark Mode</button>
        </div>
        """)

        # Status bar
        gr.HTML("""
        <div id="ds-status">
            <span class="dot"></span>
            Running locally &nbsp;·&nbsp; Google ADK 1.29 &nbsp;·&nbsp; All agents ready
        </div>
        """)

        # Quick command buttons — store refs in a list
        quick_btns: list[gr.Button] = []
        with gr.Row(elem_id="ds-quick"):
            for label, _ in QUICK_COMMANDS:
                b = gr.Button(label, elem_classes=["qbtn"], size="sm")
                quick_btns.append(b)

        # Chatbot — Gradio 6.12 uses MessageDict format natively
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

    return demo


if __name__ == "__main__":
    print()
    print("  ==========================================")
    print("   DIGITAL SENTINEL")
    print("   Personal Security & Career Orchestrator")
    print("  ==========================================")
    print()
    print("  URL : http://127.0.0.1:7860")
    print("  Stop: Ctrl+C")
    print()
    app = build_ui()
    app.launch(
        server_name="127.0.0.1",
        inbrowser=True,
        quiet=True,
        css=CSS,
        js=JS_TOGGLE,
        theme=gr.themes.Base(),
    )
