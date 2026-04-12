"""
Digital Sentinel — Usage Tracker
Logs Gemini API token usage per agent call to a local JSON file.
Exposes a get_usage_report() tool so Edwin can check spend inside the app.
"""
import json
import os
from datetime import datetime, date

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_LOG_PATH = os.path.join(_PROJECT_ROOT, "usage_log.json")

# ── Gemini 2.5 Flash pricing (USD per 1M tokens, as of April 2026) ───────────
# Input  : $0.075 / 1M tokens  (prompts <= 200k tokens)
# Output : $0.30  / 1M tokens
# Source : https://ai.google.dev/gemini-api/docs/pricing
_INPUT_COST_PER_M  = 0.075
_OUTPUT_COST_PER_M = 0.300


def _load() -> dict:
    if os.path.exists(_LOG_PATH):
        with open(_LOG_PATH) as f:
            return json.load(f)
    return {"sessions": [], "totals": {"input_tokens": 0, "output_tokens": 0, "calls": 0}}


def _save(data: dict) -> None:
    with open(_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def record_usage(agent_name: str, input_tokens: int, output_tokens: int) -> None:
    """Records a single Gemini API call to the usage log.

    Called automatically by the after_model_callback on every agent invocation.
    Not intended for direct use — the callback handles this.

    Args:
        agent_name   : Name of the agent that made the call.
        input_tokens : Prompt token count from usage_metadata.
        output_tokens: Candidates token count from usage_metadata.
    """
    data = _load()

    entry = {
        "ts": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "date": date.today().isoformat(),
        "agent": agent_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(
            (input_tokens / 1_000_000) * _INPUT_COST_PER_M
            + (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M,
            6,
        ),
    }

    data["sessions"].append(entry)
    data["totals"]["input_tokens"]  += input_tokens
    data["totals"]["output_tokens"] += output_tokens
    data["totals"]["calls"]         += 1

    _save(data)


def get_usage_report() -> str:
    """Returns a usage and cost report for all Gemini API calls made by Digital Sentinel.

    Shows token counts and estimated USD cost broken down by:
    - Today's session
    - Last 7 days per agent
    - All-time totals

    Pricing used: Gemini 2.5 Flash — $0.075/1M input tokens, $0.30/1M output tokens.

    Returns:
        Formatted usage report with token counts, costs, and a daily breakdown.
    """
    data = _load()
    sessions = data.get("sessions", [])
    totals = data.get("totals", {})

    if not sessions:
        return (
            "[Usage] No usage recorded yet.\n"
            "Usage is tracked automatically — make a few requests and check back."
        )

    today = date.today().isoformat()
    this_week = sorted(set(s["date"] for s in sessions))[-7:]

    # ── Today ──────────────────────────────────────────────────────────────────
    today_calls = [s for s in sessions if s["date"] == today]
    today_input  = sum(s["input_tokens"]  for s in today_calls)
    today_output = sum(s["output_tokens"] for s in today_calls)
    today_cost   = sum(s["cost_usd"]      for s in today_calls)

    # ── Per-agent breakdown (all time) ────────────────────────────────────────
    agents: dict[str, dict] = {}
    for s in sessions:
        a = s["agent"]
        if a not in agents:
            agents[a] = {"calls": 0, "input": 0, "output": 0, "cost": 0.0}
        agents[a]["calls"]  += 1
        agents[a]["input"]  += s["input_tokens"]
        agents[a]["output"] += s["output_tokens"]
        agents[a]["cost"]   += s["cost_usd"]

    # ── Daily totals (last 7 days) ────────────────────────────────────────────
    daily: dict[str, dict] = {}
    for s in sessions:
        d = s["date"]
        if d not in this_week:
            continue
        if d not in daily:
            daily[d] = {"calls": 0, "tokens": 0, "cost": 0.0}
        daily[d]["calls"]  += 1
        daily[d]["tokens"] += s["total_tokens"]
        daily[d]["cost"]   += s["cost_usd"]

    # ── All-time cost ─────────────────────────────────────────────────────────
    total_cost = sum(s["cost_usd"] for s in sessions)
    total_input  = totals.get("input_tokens",  0)
    total_output = totals.get("output_tokens", 0)
    total_calls  = totals.get("calls", 0)

    sep = "=" * 48
    report = f"\n{sep}\n DIGITAL SENTINEL — USAGE REPORT\n{sep}\n"
    report += f" Pricing: Gemini 2.5 Flash\n"
    report += f"   Input : $0.075 / 1M tokens\n"
    report += f"   Output: $0.300 / 1M tokens\n"

    # Today
    report += f"\n--- TODAY ({today}) ---\n"
    if today_calls:
        report += (
            f"  Calls  : {len(today_calls)}\n"
            f"  Input  : {today_input:,} tokens\n"
            f"  Output : {today_output:,} tokens\n"
            f"  Cost   : ${today_cost:.4f}\n"
        )
    else:
        report += "  No usage today yet.\n"

    # Last 7 days
    if daily:
        report += f"\n--- LAST {len(daily)} DAYS ---\n"
        for d in sorted(daily.keys(), reverse=True):
            info = daily[d]
            marker = " <- today" if d == today else ""
            report += (
                f"  {d}{marker}\n"
                f"    {info['calls']} call(s) | {info['tokens']:,} tokens | ${info['cost']:.4f}\n"
            )

    # Per-agent breakdown
    if agents:
        report += f"\n--- BY AGENT (all time) ---\n"
        for name, info in sorted(agents.items(), key=lambda x: x[1]["cost"], reverse=True):
            report += (
                f"  {name}\n"
                f"    {info['calls']} call(s) | in:{info['input']:,} out:{info['output']:,} | ${info['cost']:.4f}\n"
            )

    # All-time totals
    report += f"\n--- ALL TIME ---\n"
    report += (
        f"  Total calls  : {total_calls:,}\n"
        f"  Input tokens : {total_input:,}\n"
        f"  Output tokens: {total_output:,}\n"
        f"  Est. cost    : ${total_cost:.4f}\n"
    )
    report += f"\n  Log file: {_LOG_PATH}\n"
    report += f"{sep}\n"
    return report
