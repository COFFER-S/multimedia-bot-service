#!/usr/bin/env python3
"""
GitLab Backport Tool with Cherry-pick Support

This script implements a GitLab backport tool that can cherry-pick commits
from a source branch to a target branch using the GitLab API.

Reference implementation for the Backport Bot Service.
"""

import argparse
import sys
import os
import subprocess
import json

# ========== Auto-install Dependencies ==========
def install_requirements():
    """Auto-install required packages if not available"""
    required_packages = {
        'gitlab': 'python-gitlab',
        'requests': 'requests'
    }
    missing_packages = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("🔧 Installing missing dependencies...")
        for package in missing_packages:
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--user", package
                ])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                sys.exit(1)
        print("✅ All dependencies installed!")

install_requirements()

import gitlab
import requests

# ========== Global Configuration ==========
GITLAB_URL = "https://gitlab.espressif.cn:6688"
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "YOUR_GITLAB_TOKEN_HERE")
PROJECT_PATH = "adf/multimedia/esp-gmf"


def create_gitlab_connection():
    """Create GitLab connection with enhanced error handling"""
    if GITLAB_TOKEN == "YOUR_GITLAB_TOKEN_HERE":
        print("❌ Please set your GitLab token first!")
        sys.exit(1)
    
    try:
        gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)
        gl.auth()
        print(f"✅ Connected to {GITLAB_URL} as {gl.user.username}")
        return gl
    except gitlab.exceptions.GitlabAuthenticationError:
        print("❌ Authentication failed! Please check your GitLab token.")
        sys.exit(1)


def gitlab_cherry_pick(project_id, commit_sha, target_branch, message=None):
    """
    Cherry-pick a commit using GitLab's native cherry-pick API
    
    Returns:
        - dict: Success result
        - False: Failed
        - "conflict": Conflict
    """
    url = f"{GITLAB_URL}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/cherry_pick"
    headers = {
        "PRIVATE-TOKEN": GITLAB_TOKEN,
        "Content-Type": "application/json"
    }
    data = {"branch": target_branch}
    if message:
        data["message"] = message
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Cherry-picked commit {commit_sha[:8]} to {target_branch}")
        return result
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('message', '')
                error_code = error_data.get('error_code', '')
                
                if 'conflict' in error_code.lower():
                    print(f"⚠️ Cherry-pick conflict for {commit_sha[:8]}")
                    return "conflict"
            except:
                pass
        
        print(f"❌ Cherry-pick failed: {e}")
        return False


def backport_merge_request(project_name, source_branch, target_branch):
    """Main backport function"""
    print(f"🚀 Starting backport: {source_branch} → {target_branch}")
    
    gl = create_gitlab_connection()
    
    try:
        project = gl.projects.get(project_name)
        print(f"✅ Found project: {project.name}")
    except gitlab.exceptions.GitlabGetError:
        print(f"❌ Project '{project_name}' not found!")
        sys.exit(1)
    
    # Create backport branch
    safe_source = source_branch.replace(" ", "_").replace("~", "_").replace("^", "_")
    backport_branch = f"{safe_source}_backport"
    
    print(f"🔄 Creating backport branch: {backport_branch}")
    try:
        project.branches.create({
            'branch': backport_branch,
            'ref': target_branch
        })
    except gitlab.exceptions.GitlabCreateError as e:
        if "already exists" in str(e):
            print(f"⚠️ Branch '{backport_branch}' already exists")
        else:
            raise
    
    # Get merged MR
    mrs = project.mergerequests.list(state='merged', source_branch=source_branch)
    if not mrs:
        print(f"❌ No merged MR found for source branch '{source_branch}'")
        sys.exit(1)
    
    mr = mrs[0]
    print(f"✅ Found merged MR: !{mr.iid} - {mr.title}")
    
    # Get commits
    commits = mr.commits()
    if not commits:
        print(f"❌ No commits found in MR !{mr.iid}")
        sys.exit(1)
    
    commits_sorted = sorted(commits, key=lambda c: c.committed_date)
    print(f"📋 Found {len(commits_sorted)} commits to cherry-pick")
    
    # Cherry-pick commits
    successful = 0
    for i, c in enumerate(commits_sorted, 1):
        print(f"[{i}/{len(commits_sorted)}] {c.id[:8]} | {c.title}")
        result = gitlab_cherry_pick(project.id, c.id, backport_branch, c.title)
        if result and result != "conflict":
            successful += 1
            print(f" ✅ Cherry-picked successfully")
        elif result == "conflict":
            print(f" ⚠️ Cherry-pick conflict")
        else:
            print(f" ❌ Cherry-pick failed")
    
    # Create MR if we have at least one successful commit
    if successful > 0:
        title = f"[Backport] from {source_branch}"
        description = f"## 🤖 Automated Backport\n\n- **Source Branch:** `{source_branch}`\n- **Target Branch:** `{target_branch}`\n- **Original MR:** !{mr.iid}\n- **Commits Cherry-picked:** ✅ {successful}/{len(commits_sorted)}\n\n## ⚠️ Important Notes\n- This is an automated backport\n- **Review all changes carefully**"
        
        print(f"📝 Creating MR: {title}")
        try:
            new_mr = project.mergerequests.create({
                'source_branch': backport_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description,
                'remove_source_branch': True
            })
            print(f"🎉 Backport completed!")
            print(f"✅ Merge Request created: {new_mr.web_url}")
            return new_mr.web_url
        except Exception as e:
            print(f"❌ Failed to create MR: {e}")
            return None
    else:
        print(f"❌ No commits were successfully cherry-picked")
        return None


# ========== Command Line Entry Point ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GitLab Backport Tool with Cherry-pick Support"
    )
    parser.add_argument(
        "--project",
        help=f"GitLab project path (default: {PROJECT_PATH})"
    )
    parser.add_argument(
        "-s", "--source",
        required=True,
        help="Source branch name"
    )
    parser.add_argument(
        "-t", "--target",
        required=True,
        help="Target branch name"
    )
    
    args = parser.parse_args()
    
    project_name = args.project or PROJECT_PATH
    backport_merge_request(
        project_name,
        args.source,
        args.target
    )
