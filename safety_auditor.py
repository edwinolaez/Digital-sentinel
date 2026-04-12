import os
import requests
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class RepoAuditor:
    def __init__(self):
        # Fetch the token from .env
        self.token = os.getenv("GITHUB_PAT")
        
        # DEBUG: This helps verify if the script sees your token
        if self.token:
            print(f"--- [SYSTEM] GitHub Token detected (starts with: {self.token[:4]}...) ---")
        else:
            print("--- [SYSTEM] ⚠️ WARNING: No GITHUB_PAT found in .env file! ---")

        # Standard GitHub API Headers
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else None,
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Digital-Sentinel-Auditor"
        }

    def audit(self, repo_url):
        """
        Analyzes a GitHub repository for safety and activity metrics.
        """
        # 1. Clean and Parse URL
        try:
            repo_path = repo_url.replace("https://github.com/", "").strip("/")
            path_parts = repo_path.split("/")
            
            if len(path_parts) < 2:
                return "❌ Error: Invalid URL format. Please use 'https://github.com/owner/repo'"

            owner, repo = path_parts[0], path_parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            
        except Exception as e:
            return f"❌ Parsing Error: {str(e)}"

        # 2. Fetch Data from GitHub API
        try:
            print(f"🔍 Contacting GitHub API for: {owner}/{repo}...")
            response = requests.get(api_url, headers=self.headers)
            
            # Handle Errors
            if response.status_code == 404:
                return f"❌ Error 404: Repository '{owner}/{repo}' not found. Check your URL or Token permissions."
            elif response.status_code == 401:
                return "❌ Error 401: Unauthorized. Your GITHUB_PAT is likely incorrect."
            
            response.raise_for_status() # Catch any other HTTP errors
            data = response.json()
            
            # 3. Security & Activity Metrics
            is_archived = data.get('archived', False)
            stars = data.get('stargazers_count', 0)
            issues = data.get('open_issues_count', 0)
            description = data.get('description', 'No description provided.')
            
            # 4. Generate Final Report
            report = f"\n=========================================="
            report += f"\n🛡️  SENTINEL AUDIT: {owner.upper()} / {repo.upper()}"
            report += f"\n=========================================="
            report += f"\n📝 Description: {description}"
            report += f"\n⭐ Stars: {stars} | ⚠️ Open Issues: {issues}"
            report += f"\n📦 Archived: {'YES (Dangerous)' if is_archived else 'No (Active)'}"
            report += f"\n------------------------------------------"
            
            # Decision Logic
            if is_archived:
                report += "\nVERDICT: 🚩 DANGEROUS. This project is dead. Do not use for production."
            elif stars < 5:
                report += "\nVERDICT: ⚠️ USE CAUTION. Extremely low popularity. Check install scripts manually."
            else:
                report += "\nVERDICT: ✅ SAFE. Repository appears established and maintained."
            
            report += "\n==========================================\n"
            return report

        except requests.exceptions.RequestException as e:
            return f"❌ Connection Error: {str(e)}"

# This block allows the script to be run by itself
if __name__ == "__main__":
    auditor = RepoAuditor()
    print("\n--- Digital Sentinel: Repo Safety Tool ---")
    url = input("Paste GitHub URL to scan: ").strip()
    
    if url:
        print(auditor.audit(url))
    else:
        print("❌ No URL provided.")