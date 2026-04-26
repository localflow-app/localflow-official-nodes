import re
import time

import requests


def _has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text)) if text else False


def execute(self, input_data):
    github_entries = input_data.get("github_entries", [])
    apps_data = input_data.get("apps_data", [])
    token = self.config.get("github_token", "")
    delay = self.config.get("delay_seconds", 0.5)

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen = {}
    for entry in github_entries:
        key = entry["owner_repo"].lower()
        if key not in seen:
            seen[key] = entry["owner_repo"]

    repo_desc_map = {}

    unique_repos = list(seen.values())
    for i, owner_repo in enumerate(unique_repos):
        report_progress(int(i / len(unique_repos) * 100), f"获取 {owner_repo} 描述...")
        url = f"https://api.github.com/repos/{owner_repo}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                github_desc = data.get("description", "") or ""
                repo_desc_map[owner_repo.lower()] = github_desc
            else:
                repo_desc_map[owner_repo.lower()] = ""
        except Exception:
            repo_desc_map[owner_repo.lower()] = ""
        if i < len(unique_repos) - 1:
            time.sleep(delay)

    entries_with_desc = []
    for entry in github_entries:
        idx = entry["index"]
        key = entry["owner_repo"].lower()
        github_desc = repo_desc_map.get(key, "")
        existing_desc = apps_data[idx].get("description", {}) if 0 <= idx < len(apps_data) else {}

        if isinstance(existing_desc, str):
            existing_desc = {"en": existing_desc, "cn": ""}

        entries_with_desc.append({
            **entry,
            "github_description": github_desc,
            "existing_description": existing_desc,
        })

    return {
        **input_data,
        "github_entries": entries_with_desc,
        "repo_desc_map": repo_desc_map,
    }
