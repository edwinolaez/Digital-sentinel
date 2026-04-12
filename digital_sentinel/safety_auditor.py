import os
import requests
from dotenv import load_dotenv

load_dotenv()


class RepoAuditor:
    def __init__(self):
        self.token = os.getenv("GITHUB_PAT")
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else None,
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Digital-Sentinel-Auditor",
        }

    def audit(self, repo_url):
        try:
            repo_path = repo_url.replace("https://github.com/", "").strip("/")
            path_parts = repo_path.split("/")
            if len(path_parts) < 2:
                return "[Error] Invalid URL. Use: https://github.com/owner/repo"
            owner, repo = path_parts[0], path_parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
        except Exception as e:
            return f"[Error] Could not parse URL: {e}"

        try:
            response = requests.get(api_url, headers=self.headers, timeout=10)
            if response.status_code == 404:
                return f"[Error 404] Repository not found: {owner}/{repo}"
            elif response.status_code == 401:
                return "[Error 401] Unauthorized -- check your GITHUB_PAT in .env."
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            return f"[Connection Error] {e}"

        is_archived  = data.get("archived", False)
        stars        = data.get("stargazers_count", 0)
        issues       = data.get("open_issues_count", 0)
        description  = data.get("description") or "No description provided."
        forks        = data.get("forks_count", 0)
        last_push    = (data.get("pushed_at") or "unknown")[:10]
        license_info = (data.get("license") or {}).get("spdx_id", "None")

        if is_archived:
            verdict = "DANGEROUS -- project is archived/dead. Do not use."
        elif stars < 5:
            verdict = "CAUTION -- extremely low stars. Inspect install scripts manually."
        elif last_push < "2023-01-01":
            verdict = "CAUTION -- last push over 2 years ago. May be unmaintained."
        else:
            verdict = "SAFE -- repository appears active and established."

        archived_str = "YES" if is_archived else "No"
        sep  = "=" * 44
        dash = "-" * 44
        lines = [
            sep,
            f" SENTINEL AUDIT: {owner}/{repo}",
            sep,
            f" Description : {description}",
            f" Stars       : {stars:,}   Forks: {forks:,}   Open Issues: {issues}",
            f" Last push   : {last_push}",
            f" License     : {license_info}",
            f" Archived    : {archived_str}",
            dash,
            f" VERDICT: {verdict}",
            sep,
        ]
        NL = chr(10)
        return NL + NL.join(lines) + NL


if __name__ == "__main__":
    auditor = RepoAuditor()
    print("--- Digital Sentinel: Repo Safety Tool ---")
    url = input("Paste GitHub URL to scan: ").strip()
    if url:
        print(auditor.audit(url))
    else:
        print("[Error] No URL provided.")
