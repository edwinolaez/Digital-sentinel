"""
Digital Sentinel — GitHub Trending Scout
Fetches recently created, fast-rising repositories across your tech stack
and AI/ML domains, returning raw structured data for AI trend analysis.
"""
import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

_GITHUB_API = "https://api.github.com/search/repositories"


def _search_repos(query: str, token: str, per_page: int = 8) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = requests.get(
            _GITHUB_API,
            headers=headers,
            params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.exceptions.HTTPError as e:
        return [{"_error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}]
    except Exception as e:
        return [{"_error": str(e)}]


def _format_repo(repo: dict) -> str:
    name = repo.get("full_name", "?")
    desc = (repo.get("description") or "No description").replace("\n", " ")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    lang = repo.get("language") or "?"
    topics = ", ".join(repo.get("topics", [])[:8]) or "none"
    created = (repo.get("created_at") or "")[:10]
    url = repo.get("html_url", "")
    return (
        f"  Repo   : {name}\n"
        f"  Stars  : {stars}  Forks: {forks}  Language: {lang}\n"
        f"  Created: {created}\n"
        f"  Topics : {topics}\n"
        f"  Desc   : {desc}\n"
        f"  URL    : {url}"
    )


def fetch_github_trending(days_back: int = 7) -> str:
    """Fetches recently created, fast-rising GitHub repositories across your tech stack and AI domains.

    Queries GitHub for repos created in the last N days with high star velocity,
    spanning Python, TypeScript, JavaScript, React/Next.js, and AI/LLM categories.
    The output is raw structured data intended for downstream AI trend analysis.

    Args:
        days_back: How many days back to search for new repos (default 7).
                   Use 14 or 30 for broader coverage.

    Returns:
        Structured text listing trending repos grouped by category, including
        star counts, topics, descriptions, and URLs — ready for trend synthesis.
    """
    token = os.getenv("GITHUB_PAT")
    if not token:
        return "[TrendScout] Error: GITHUB_PAT missing from .env"

    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    min_stars = "stars:>5"

    # Each tuple: (display label, GitHub search query)
    categories = [
        (
            "AI / LLM / Agents",
            f"topic:llm created:>{since} {min_stars}",
        ),
        (
            "AI / LLM / Agents (agents topic)",
            f"topic:ai-agents created:>{since} {min_stars}",
        ),
        (
            "Python",
            f"language:Python created:>{since} stars:>20",
        ),
        (
            "TypeScript",
            f"language:TypeScript created:>{since} stars:>15",
        ),
        (
            "JavaScript",
            f"language:JavaScript created:>{since} stars:>15",
        ),
        (
            "React / Next.js",
            f"topic:react created:>{since} {min_stars}",
        ),
        (
            "DevTools / CLI",
            f"topic:cli created:>{since} stars:>10",
        ),
        (
            "Open Source AI Models / Inference",
            f"topic:inference created:>{since} {min_stars}",
        ),
    ]

    seen: set[str] = set()
    sections: list[str] = []

    for label, query in categories:
        items = _search_repos(query, token)

        # Surface any API errors
        errors = [r["_error"] for r in items if "_error" in r]
        if errors:
            sections.append(f"\n[{label}]\n  ERROR: {errors[0]}")
            continue

        # Deduplicate across categories
        unique = [r for r in items if r.get("full_name") and r["full_name"] not in seen]
        seen.update(r["full_name"] for r in unique)

        if unique:
            formatted = "\n\n".join(_format_repo(r) for r in unique[:5])
            sections.append(f"\n[{label}]\n{formatted}")

    if not sections:
        return (
            "[TrendScout] No trending repositories found. "
            "Check your GITHUB_PAT or try a larger days_back value."
        )

    header = (
        f"=== GITHUB TRENDING RAW DATA (last {days_back} days | fetched {datetime.utcnow().strftime('%Y-%m-%d')}) ===\n"
        f"Categories scanned: {len(categories)} | Unique repos: {len(seen)}\n"
    )
    return header + "".join(sections)
