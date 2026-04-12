import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
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
        """Analyzes a GitHub repository for safety and activity metrics."""
        # 1. Parse URL
        try:
            repo_path = repo_url.replace("https://github.com/", "").strip("/")
            path_parts = repo_path.split("/")
            if len(path_parts) < 2:
                return "[Error] Invalid URL. Use: https://github.com/owner/repo"
            owner, repo = path_parts[0], path_parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
        except Exception as e:
            return f"[Error] Could not parse URL: {e}"

        # 2. Fetch from GitHub API
        try:
            response = requests.get(api_url, headers=self.headers, timeout=10)
            if response.status_code == 404:
                return f"[Error 404] Repository '{owner}/{repo}' not found."
            elif response.status_code == 401:
                return "[Error 401] Unauthorized — check your GITHUB_PAT in .env."
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            return f"[Connection Error] {e}"

        # 3. Metrics
        is_archived  = data.get("archived", False)
        stars        = data.get("stargazers_count", 0)
        issues       = data.get("open_issues_count", 0)
        description  = data.get("description") or "No description provided."
        forks        = data.get("forks_count", 0)
        last_push    = data.get("pushed_at", "unknown")[:10]
        license_info = (data.get("license") or {}).get("spdx_id", "None")

        # 4. Verdict
        if is_archived:
            verdict = "DANGEROUS — project is archived/dead. Do not use."
        elif stars < 5:
            verdict = "CAUTION — extremely low stars. Inspect install scripts manually."
        elif last_push < "2023-01-01":
            verdict = "CAUTION — last push was over 2 years ago. May be unmaintained."
        else:
            verdict = "SAFE — repository appears active and established."

        report  = "\n" + "=" * 44
        report += f"\n SENTINEL AUDIT: {owner}/{repo}"
        report += "\n" + "=" * 44
        report += f"\n Description : {description}"
        report += f"\n Stars       : {stars:,}   Forks: {forks:,}   Open Issues: {issues}"
        report += f"\n Last push   : {last_push}"
        report += f"\n License     : {license_info}"
        report += f"\n Archived    : {'YES' if is_archived else 'No'}"
        report += "\n" + "-" * 44
        report += f"\n VERDICT: {verdict}"
        report += "\n" + "=" * 44 + "\n"
        return report

# This block allows the script to be run by itself
if __name__ == "__main__":
    auditor = RepoAuditor()
    print("\n--- Digital Sentinel: Repo Safety Tool ---")
    url = input("Paste GitHub URL to scan: ").strip()
    
    if url:
        print(auditor.audit(url))
    else:
        print("❌ No URL provided.")