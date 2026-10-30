"""
DevVault - GitHub Integration Service
Provides seamless connectivity to GitHub REST API:
- User profile verification and repository discovery
- One-click repository import to DevVault project
- Live repository metadata sync (stars, forks, open issues, branch)
- Latest commit history retrieval
- Remote README.md extraction into project documentation
"""
import re
import base64
import requests
from datetime import datetime

class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, token=None):
        self.token = token.strip() if token else None

    def _get_headers(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevVault-Project-Management-System"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def parse_repo_url(url):
        """Extracts (owner, repo) from GitHub URL or slug string."""
        if not url:
            return None, None
        
        # Clean trailing slashes, .git suffix
        url = url.strip().rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]

        # Match https://github.com/owner/repo or github.com/owner/repo or owner/repo
        match = re.search(r'(?:github\.com/|^)([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)', url)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def get_user_profile(self, username):
        """Fetches public profile for a GitHub user."""
        if not username:
            return {"success": False, "error": "Username is required."}

        url = f"{self.BASE_URL}/users/{username.strip()}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "data": {
                        "username": data.get("login"),
                        "name": data.get("name") or data.get("login"),
                        "avatar_url": data.get("avatar_url"),
                        "html_url": data.get("html_url"),
                        "bio": data.get("bio") or "",
                        "public_repos": data.get("public_repos", 0),
                        "followers": data.get("followers", 0),
                        "following": data.get("following", 0),
                        "created_at": data.get("created_at")
                    }
                }
            elif resp.status_code == 404:
                return {"success": False, "error": f"GitHub user '{username}' was not found."}
            elif resp.status_code == 403:
                return {"success": False, "error": "GitHub API rate limit exceeded. Add a Personal Access Token for 5,000 requests/hr."}
            else:
                return {"success": False, "error": f"GitHub API error (Status {resp.status_code})."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error connecting to GitHub: {str(e)}"}

    def get_user_repositories(self, username, per_page=100):
        """Fetches public repositories owned by the user, sorted by updated date."""
        if not username:
            return {"success": False, "error": "Username is required."}

        url = f"{self.BASE_URL}/users/{username.strip()}/repos"
        params = {"sort": "updated", "per_page": per_page}

        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            if resp.status_code == 200:
                raw_repos = resp.json()
                clean_repos = []
                for r in raw_repos:
                    clean_repos.append({
                        "name": r.get("name"),
                        "full_name": r.get("full_name"),
                        "description": r.get("description") or "No description provided.",
                        "html_url": r.get("html_url"),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "open_issues": r.get("open_issues_count", 0),
                        "language": r.get("language") or "Other",
                        "topics": r.get("topics", []),
                        "default_branch": r.get("default_branch", "main"),
                        "is_private": r.get("private", False),
                        "updated_at": r.get("updated_at")
                    })
                return {"success": True, "repos": clean_repos}
            elif resp.status_code == 404:
                return {"success": False, "error": f"User '{username}' not found."}
            elif resp.status_code == 403:
                return {"success": False, "error": "GitHub rate limit exceeded. Please configure a personal access token."}
            else:
                return {"success": False, "error": f"Failed to fetch repositories (HTTP {resp.status_code})."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network connection error: {str(e)}"}

    def get_repo_details(self, owner, repo):
        """Fetches live repository stats (stars, forks, open issues, description)."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=8)
            if resp.status_code == 200:
                d = resp.json()
                return {
                    "success": True,
                    "data": {
                        "name": d.get("name"),
                        "full_name": d.get("full_name"),
                        "description": d.get("description") or "",
                        "html_url": d.get("html_url"),
                        "stars": d.get("stargazers_count", 0),
                        "forks": d.get("forks_count", 0),
                        "open_issues": d.get("open_issues_count", 0),
                        "watchers": d.get("watchers_count", 0),
                        "default_branch": d.get("default_branch", "main"),
                        "language": d.get("language") or "Code",
                        "topics": d.get("topics", []),
                        "license": d.get("license", {}).get("spdx_id") if d.get("license") else None,
                        "updated_at": d.get("updated_at")
                    }
                }
            elif resp.status_code == 404:
                return {"success": False, "error": f"Repository '{owner}/{repo}' not found on GitHub."}
            elif resp.status_code == 403:
                return {"success": False, "error": "Rate limit exceeded. Provide a personal access token in settings."}
            return {"success": False, "error": f"GitHub returned status {resp.status_code}."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error: {str(e)}"}

    def get_recent_commits(self, owner, repo, limit=5):
        """Fetches the latest commit log for a repository."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {"per_page": limit}
        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=8)
            if resp.status_code == 200:
                commits = []
                for item in resp.json():
                    commit_obj = item.get("commit", {})
                    author_obj = commit_obj.get("author", {})
                    committer_user = item.get("author") or {}
                    
                    # Parse ISO timestamp
                    date_str = author_obj.get("date")
                    dt_formatted = ""
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            dt_formatted = dt.strftime("%b %d, %Y")
                        except Exception:
                            dt_formatted = date_str[:10]

                    commits.append({
                        "sha": item.get("sha"),
                        "short_sha": item.get("sha")[:7] if item.get("sha") else "",
                        "message": commit_obj.get("message", "").split("\n")[0],  # first line of commit
                        "author_name": author_obj.get("name") or "Unknown",
                        "author_avatar": committer_user.get("avatar_url") or "",
                        "date": dt_formatted,
                        "html_url": item.get("html_url")
                    })
                return {"success": True, "commits": commits}
            return {"success": False, "error": f"Could not retrieve commits (HTTP {resp.status_code})."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error: {str(e)}"}

    def get_repo_readme(self, owner, repo):
        """Fetches raw markdown content of the default README."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/readme"
        headers = self._get_headers()
        # Request raw markdown content
        headers["Accept"] = "application/vnd.github.v3.raw"
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                return {"success": True, "content": resp.text}
            elif resp.status_code == 404:
                return {"success": False, "error": "No README.md found in repository."}
            return {"success": False, "error": f"GitHub status {resp.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error: {str(e)}"}

