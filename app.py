#!/usr/bin/env python3
"""
Simple Web UI for GitHub Contribution Backfiller
Side-by-side layout + 52-Week Contribution Calendar.
Uses only Python Standard Library (no pip installs needed).
"""

import datetime
import http.server
import json
import os
import random
import socketserver
import subprocess
import sys
import urllib.parse
import webbrowser
from collections import Counter

PORT = 8765
REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def get_git_info():
    def run_cmd(cmd):
        try:
            res = subprocess.run(
                cmd, cwd=REPO_DIR, capture_output=True, text=True, check=True
            )
            return res.stdout.strip()
        except Exception:
            return ""

    user_name = run_cmd(["git", "config", "user.name"]) or "User"
    user_email = run_cmd(["git", "config", "user.email"]) or "user@example.com"
    remote_url = run_cmd(["git", "remote", "get-url", "origin"]) or "No remote"
    branch = (
        run_cmd(["git", "branch", "--show-current"])
        or run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        or "main"
    )
    if branch == "HEAD":
        branch = "main"
    commit_count = run_cmd(["git", "rev-list", "--count", "HEAD"]) or "0"

    return {
        "user_name": user_name,
        "user_email": user_email,
        "remote_url": remote_url,
        "branch": branch,
        "commit_count": commit_count,
    }


def get_existing_commits():
    try:
        res = subprocess.run(
            ["git", "log", "--format=%ad", "--date=short"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        dates = res.stdout.strip().splitlines()
        return dict(Counter(dates))
    except Exception:
        return {}


def simulate_backfill(start_date_str, end_date_str, min_c, max_c, freq, skip_wk, only_empty, existing_map=None):
    if not start_date_str or not end_date_str:
        return {"commits_by_date": {}, "total_commits": 0, "active_days": 0, "total_days": 0}

    try:
        start = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except Exception:
        return {"commits_by_date": {}, "total_commits": 0, "active_days": 0, "total_days": 0}

    if start > end:
        start, end = end, start

    low = min(int(min_c), int(max_c))
    high = max(int(min_c), int(max_c))
    if low < 1:
        low = 1
    if high < low:
        high = low

    if existing_map is None:
        existing_map = get_existing_commits()

    curr = start
    commits_by_date = {}
    total_commits = 0
    active_days = 0
    total_days = (end - start).days + 1

    while curr <= end:
        date_str = curr.strftime("%Y-%m-%d")
        is_wk = curr.weekday() >= 5
        existing_count = existing_map.get(date_str, 0)

        if only_empty and existing_count > 0:
            commits_by_date[date_str] = 0
            curr += datetime.timedelta(days=1)
            continue

        if skip_wk and is_wk:
            commits_by_date[date_str] = 0
            curr += datetime.timedelta(days=1)
            continue

        if random.random() <= freq:
            count = random.randint(low, high) if high > low else low
            commits_by_date[date_str] = count
            total_commits += count
            active_days += 1
        else:
            commits_by_date[date_str] = 0

        curr += datetime.timedelta(days=1)

    return {
        "commits_by_date": commits_by_date,
        "total_commits": total_commits,
        "active_days": active_days,
        "total_days": total_days,
    }


def execute_backfill(start_date_str, end_date_str, min_c, max_c, freq, skip_wk, only_empty, existing_map=None, commit_plan=None):
    total_commits = 0
    active_days = 0
    log_file = os.path.join(REPO_DIR, "activity.txt")
    env = os.environ.copy()
    logs = []

    # If an exact visual commitPlan was generated in the preview, execute it faithfully!
    if commit_plan and isinstance(commit_plan, dict):
        sorted_dates = sorted(commit_plan.keys())
        for date_str in sorted_dates:
            count = int(commit_plan.get(date_str, 0))
            if count <= 0:
                continue
            active_days += 1
            curr = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            for _ in range(count):
                total_commits += 1
                # Use hours between 11:00 and 16:00 so date never drifts across UTC / IST boundaries
                hour = random.randint(11, 16)
                minute = random.randint(0, 59)
                sec = random.randint(0, 59)
                commit_dt = datetime.datetime.combine(curr, datetime.time(hour, minute, sec))
                dt_iso = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")

                env["GIT_AUTHOR_DATE"] = dt_iso
                env["GIT_COMMITTER_DATE"] = dt_iso

                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"Contribution entry on {dt_iso} (#{total_commits})\n")

                subprocess.run(
                    ["git", "add", "activity.txt"],
                    cwd=REPO_DIR,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["git", "commit", "-m", f"chore: backfill activity log {dt_iso}"],
                    cwd=REPO_DIR,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            logs.append(f"Added commits for {date_str} (+{count} commits)")

        return {
            "success": True,
            "total_commits": total_commits,
            "active_days": active_days,
            "total_days": len(sorted_dates),
            "logs": logs,
        }

    # Fallback if no commit_plan provided (e.g. CLI)
    if not start_date_str or not end_date_str:
        raise ValueError("Please provide valid start and end dates.")

    start = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

    if start > end:
        start, end = end, start

    low = min(int(min_c), int(max_c))
    high = max(int(min_c), int(max_c))
    if low < 1:
        low = 1
    if high < low:
        high = low

    if existing_map is None:
        existing_map = get_existing_commits()

    curr = start
    total_days = (end - start).days + 1

    while curr <= end:
        date_str = curr.strftime("%Y-%m-%d")
        is_wk = curr.weekday() >= 5
        existing_count = existing_map.get(date_str, 0)

        if only_empty and existing_count > 0:
            curr += datetime.timedelta(days=1)
            continue

        if skip_wk and is_wk:
            curr += datetime.timedelta(days=1)
            continue

        if random.random() <= freq:
            active_days += 1
            count = random.randint(low, high) if high > low else low
            for _ in range(count):
                total_commits += 1
                hour = random.randint(11, 16)
                minute = random.randint(0, 59)
                sec = random.randint(0, 59)
                commit_dt = datetime.datetime.combine(curr, datetime.time(hour, minute, sec))
                dt_iso = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")

                env["GIT_AUTHOR_DATE"] = dt_iso
                env["GIT_COMMITTER_DATE"] = dt_iso

                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"Contribution entry on {dt_iso} (#{total_commits})\n")

                subprocess.run(
                    ["git", "add", "activity.txt"],
                    cwd=REPO_DIR,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["git", "commit", "-m", f"chore: backfill activity log {dt_iso}"],
                    cwd=REPO_DIR,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if active_days % 10 == 0 or curr == end:
                logs.append(f"Added commits for {date_str} (+{count} commits)")

        curr += datetime.timedelta(days=1)

    return {
        "success": True,
        "total_commits": total_commits,
        "active_days": active_days,
        "total_days": total_days,
        "logs": logs,
    }


def execute_push():
    try:
        remote_check = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        if remote_check.returncode != 0 or not remote_check.stdout.strip():
            return {
                "success": False,
                "error": "No remote 'origin' configured. Set one with:\n  git remote add origin https://github.com/<username>/<repo>.git",
            }

        branch_res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
        )
        branch = branch_res.stdout.strip()
        if not branch or branch == "HEAD":
            branch = "main"

        res = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return {"success": True, "output": (res.stdout + res.stderr).strip() or f"Pushed successfully to {branch}."}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": (e.stderr or e.stdout or str(e)).strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GitHub Contributions Backfiller</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --accent: #238636;
      --accent-hover: #2ea043;
      --blue: #58a6ff;
      --danger: #f85149;
      --lvl-0: #161b22;
      --lvl-1: #0e4429;
      --lvl-2: #006d32;
      --lvl-3: #26a641;
      --lvl-4: #39d353;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 20px 24px; min-width: 1100px; }
    .container { max-width: 1320px; margin: 0 auto; }
    
    header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
    .badge { font-size: 12px; background: #21262d; padding: 3px 8px; border-radius: 12px; border: 1px solid var(--border); color: var(--blue); }
    .user-info { display: flex; gap: 16px; font-size: 13px; color: var(--text-muted); margin-top: 5px; }
    .user-info span strong { color: var(--text); }
    
    /* SIDE-BY-SIDE MAIN LAYOUT */
    .main-layout {
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 20px;
      align-items: start;
    }
    
    .sidebar { display: flex; flex-direction: column; gap: 16px; }
    .content-area { display: flex; flex-direction: column; gap: 16px; }
    
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
    .card-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    
    .form-group { margin-bottom: 12px; }
    label { display: block; font-size: 12.5px; color: var(--text-muted); margin-bottom: 5px; font-weight: 500; }
    input[type="date"], input[type="number"], select {
      width: 100%; background: #0d1117; border: 1px solid var(--border); color: var(--text);
      padding: 7px 10px; border-radius: 6px; font-size: 13px; outline: none;
    }
    input[type="date"]:focus, input[type="number"]:focus { border-color: var(--blue); }
    
    .slider-container { display: flex; align-items: center; gap: 10px; }
    input[type="range"] { flex: 1; accent-color: var(--accent-hover); cursor: pointer; }
    
    .presets { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
    .btn-preset { background: #21262d; border: 1px solid var(--border); color: var(--text); padding: 5px 8px; border-radius: 6px; font-size: 11.5px; cursor: pointer; transition: 0.15s; }
    .btn-preset:hover { background: #30363d; border-color: var(--text-muted); }
    .btn-preset.highlight { background: rgba(35, 134, 54, 0.25); border-color: var(--accent); color: #7ee787; font-weight: 600; }
    
    .checkbox-label { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; cursor: pointer; user-select: none; line-height: 1.4; color: var(--text); }
    .checkbox-label input { margin-top: 2px; }
    
    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; transition: 0.2s; }
    .btn-primary { background: var(--accent); color: #fff; width: 100%; }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-secondary { background: #21262d; border: 1px solid var(--border); color: var(--text); }
    .btn-secondary:hover { background: #30363d; }
    .btn-blue { background: #1f6feb; color: #fff; }
    .btn-blue:hover { background: #388bfd; }
    
    /* GitHub Exact Calendar Layout */
    .gh-calendar-container {
      background: #0d1117;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 18px 14px 18px;
      overflow-x: auto;
    }
    .gh-calendar-wrapper {
      display: inline-block;
      min-width: 860px;
    }
    .gh-months-row {
      position: relative;
      height: 22px;
      margin-left: 32px;
      margin-bottom: 6px;
    }
    .gh-month-label {
      position: absolute;
      font-size: 12px;
      font-weight: 600;
      color: #c9d1d9;
      white-space: nowrap;
      user-select: none;
      letter-spacing: 0.2px;
    }
    .gh-body {
      display: flex;
      gap: 8px;
    }
    .gh-days-labels {
      display: grid;
      grid-template-rows: repeat(7, 12px);
      row-gap: 3.5px;
      font-size: 11px;
      font-weight: 600;
      color: #c9d1d9;
      width: 24px;
      text-align: right;
      line-height: 12px;
      user-select: none;
    }
    .gh-grid {
      display: grid;
      grid-auto-flow: column;
      grid-template-rows: repeat(7, 12px);
      grid-template-columns: repeat(53, 12px);
      gap: 3.5px;
    }
    .day-cell {
      width: 12px;
      height: 12px;
      border-radius: 2px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      cursor: pointer;
      position: relative;
    }
    .day-cell:hover {
      outline: 1.5px solid #fff;
      z-index: 5;
    }
    
    .lvl-0 { background-color: var(--lvl-0); }
    .lvl-1 { background-color: var(--lvl-1); }
    .lvl-2 { background-color: var(--lvl-2); }
    .lvl-3 { background-color: var(--lvl-3); }
    .lvl-4 { background-color: var(--lvl-4); }
    
    /* Highlight for new proposed commits */
    .is-new {
      box-shadow: 0 0 0 1px #58a6ff inset;
      animation: pulse 1.8s infinite alternate;
    }
    @keyframes pulse {
      0% { opacity: 0.85; }
      100% { opacity: 1; }
    }
    
    .legend-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 10px;
      font-size: 11.5px;
      color: var(--text-muted);
    }
    .legend-boxes {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .legend-box {
      width: 11px;
      height: 11px;
      border-radius: 2px;
    }
    
    .terminal-box {
      background: #090d13;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 10px 12px;
      font-family: monospace;
      font-size: 11.5px;
      color: #7ee787;
      height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    .log-dim { color: var(--text-muted); }
    .log-err { color: var(--danger); }
    .log-info { color: var(--blue); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>
          GitHub Contribution Backfiller
          <span class="badge" id="branchBadge">main</span>
        </h1>
        <div class="user-info">
          <span>GitHub User: <strong id="userName" style="cursor:pointer; text-decoration:underline;" title="Click to change username" onclick="changeUsername()">Loading...</strong> <small style="color:var(--text-muted); cursor:pointer;" onclick="changeUsername()">[edit]</small></span>
          <span>Email: <strong id="userEmail">Loading...</strong></span>
          <span>Profile Total: <strong id="profileTotal" style="color:#7ee787;">...</strong> contributions</span>
        </div>
      </div>
      <div>
        <button class="btn btn-blue" id="btnPush" onclick="pushToGitHub()">
          ⬆️ Push to GitHub
        </button>
      </div>
    </header>

    <!-- SIDE-BY-SIDE LAYOUT -->
    <div class="main-layout">
      
      <!-- LEFT SIDEBAR: Controls -->
      <div class="sidebar">
        <!-- 1. Date Range -->
        <div class="card">
          <div class="card-title">
            <span>📅 1. Select Date Range</span>
          </div>
          <div class="presets">
            <button class="btn-preset highlight" data-preset="past-year" onclick="setPreset('past-year', this)">
              Past 1 Year (52 Wks)
            </button>
            <button class="btn-preset" data-preset="past-6-months" onclick="setPreset('past-6-months', this)">
              Past 6 Months
            </button>
            <button class="btn-preset" data-preset="past-3-months" onclick="setPreset('past-3-months', this)">
              Past 3 Months
            </button>
            <button class="btn-preset" data-preset="current-month" onclick="setPreset('current-month', this)">
              Current Month
            </button>
            <button class="btn-preset" data-preset="current-year" onclick="setPreset('current-year', this)">
              Current Year (YTD)
            </button>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
            <div class="form-group" style="margin-bottom:0;">
              <label>Start Date</label>
              <input type="date" id="startDate" oninput="onDateInputChanged()" onchange="onDateInputChanged()" />
            </div>
            <div class="form-group" style="margin-bottom:0;">
              <label>End Date</label>
              <input type="date" id="endDate" oninput="onDateInputChanged()" onchange="onDateInputChanged()" />
            </div>
          </div>
          <div>
            <label class="checkbox-label">
              <input type="checkbox" id="onlyEmptyDays" checked onchange="runPreview()" />
              <span><strong>Smart Gap Fill:</strong> Only commit on empty days (don't overwrite active days)</span>
            </label>
          </div>
        </div>

        <!-- 2. Intensity & Frequency -->
        <div class="card">
          <div class="card-title">
            <span>⚡ 2. Intensity & Frequency</span>
          </div>
          <div class="form-group">
            <label>Commits per Day: <span id="lblCommits" style="color:var(--blue); font-weight:600;">2 - 5 commits</span></label>
            <div style="display: flex; gap: 8px;">
              <div style="flex:1;">
                <small style="color:var(--text-muted); font-size:11px;">Min</small>
                <input type="number" id="minCommits" min="1" max="15" value="2" oninput="validateCounts(); runPreview();" />
              </div>
              <div style="flex:1;">
                <small style="color:var(--text-muted); font-size:11px;">Max</small>
                <input type="number" id="maxCommits" min="1" max="25" value="5" oninput="validateCounts(); runPreview();" />
              </div>
            </div>
          </div>

          <div class="form-group" style="margin-top: 10px;">
            <label>Day Activity Rate: <span id="lblFreq" style="color:var(--blue); font-weight:600;">85%</span> of days</label>
            <div class="slider-container">
              <input type="range" id="freqSlider" min="20" max="100" value="85" oninput="updateLabels()" onchange="runPreview()" />
            </div>
          </div>

          <div style="margin-bottom: 14px;">
            <label class="checkbox-label">
              <input type="checkbox" id="skipWeekends" onchange="runPreview()" />
              <span>Skip weekends (Saturdays & Sundays)</span>
            </label>
          </div>

          <button class="btn btn-primary" id="btnGenerate" onclick="generateCommits()">
            🚀 Generate Commits
          </button>
        </div>
      </div>

      <!-- RIGHT CONTENT AREA: Live Preview + Console -->
      <div class="content-area">
        <!-- Live Contribution Graph -->
        <div class="card">
          <div class="card-title">
            <span>🟩 Contribution Graph Live Preview (52 Weeks)</span>
            <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="runPreview()">
              🔄 Refresh Preview
            </button>
          </div>

          <div class="gh-calendar-container">
            <div class="gh-calendar-wrapper">
              <!-- Month labels -->
              <div class="gh-months-row" id="monthsRow"></div>
              
              <div class="gh-body">
                <!-- Day labels -->
                <div class="gh-days-labels">
                  <div></div>
                  <div>Mon</div>
                  <div></div>
                  <div>Wed</div>
                  <div></div>
                  <div>Fri</div>
                  <div></div>
                </div>

                <!-- 53 columns x 7 rows grid -->
                <div class="gh-grid" id="calendarGrid"></div>
              </div>
            </div>
          </div>

          <div class="legend-row">
            <div>
              <span>Existing: <strong id="statExistingDays" style="color:var(--text);">0</strong> active days</span> |
              <span>Adding: <strong id="statNewActive" style="color:#58a6ff;">0</strong> days (<strong id="statNewCommits" style="color:#7ee787;">0</strong> commits)</span>
            </div>
            <div class="legend-boxes">
              <span>Less</span>
              <div class="legend-box lvl-0"></div>
              <div class="legend-box lvl-1"></div>
              <div class="legend-box lvl-2"></div>
              <div class="legend-box lvl-3"></div>
              <div class="legend-box lvl-4"></div>
              <span>More</span>
              <span style="margin-left: 8px; font-size:11px; color:#58a6ff;">[Blue border = Previewed new commits]</span>
            </div>
          </div>
        </div>

        <!-- Activity Console -->
        <div class="card">
          <div class="card-title" style="margin-bottom:6px;">📋 Activity Console</div>
          <div class="terminal-box" id="terminalLog">[Ready] Graph matches your GitHub calendar. Select dates and click 'Generate Commits'.</div>
        </div>
      </div>

    </div>
  </div>

  <script>
    let existingCommitsMap = {};
    let simulatedCommitsMap = {};
    let calendarDays = [];
    let debounceTimer = null;

    function log(msg, type = "dim") {
      const box = document.getElementById("terminalLog");
      const time = new Date().toLocaleTimeString();
      let colorClass = "log-dim";
      if (type === "err") colorClass = "log-err";
      if (type === "info") colorClass = "log-info";
      box.innerHTML += `\\n<span class="${colorClass}">[${time}] ${msg}</span>`;
      box.scrollTop = box.scrollHeight;
    }

    async function loadGitInfo() {
      try {
        const res = await fetch("/api/info");
        const data = await res.json();
        const detectedUser = data.user_name || "User";
        document.getElementById("userName").textContent = detectedUser;
        document.getElementById("userEmail").textContent = data.user_email || "Not configured";
        document.getElementById("branchBadge").textContent = data.branch || "main";
        if (!githubUsername) {
          githubUsername = detectedUser;
        }
      } catch (e) {
        log("Could not load repo info: " + e.message, "err");
      }
    }

    let githubUsername = "";

    function changeUsername() {
      const current = githubUsername || document.getElementById("userName").textContent.trim();
      const nextUser = prompt("Enter GitHub Username to fetch contributions for:", current);
      if (nextUser && nextUser.trim()) {
        githubUsername = nextUser.trim();
        document.getElementById("userName").textContent = githubUsername;
        loadExistingCommits();
      }
    }

    async function loadExistingCommits() {
      try {
        const res = await fetch("/api/existing_commits");
        existingCommitsMap = await res.json();
      } catch (e) {
        existingCommitsMap = {};
      }

      const user = githubUsername || document.getElementById("userName").textContent.trim();

      try {
        const ghUrl = `https://github-contributions-api.jogruber.de/v4/${user}?y=last`;
        const ghRes = await fetch(ghUrl);
        if (ghRes.ok) {
          const ghData = await ghRes.json();
          if (ghData.contributions) {
            ghData.contributions.forEach(item => {
              if (item.count > 0) {
                existingCommitsMap[item.date] = Math.max(existingCommitsMap[item.date] || 0, item.count);
              }
            });
            const currentYear = new Date().getFullYear();
            const totalCount = (ghData.total && (ghData.total[currentYear] || Object.values(ghData.total).pop())) || "0";
            document.getElementById("profileTotal").textContent = `${totalCount}+`;
          }
        }
      } catch (err) {}

      let activeCount = Object.values(existingCommitsMap).filter(c => c > 0).length;
      document.getElementById("statExistingDays").textContent = activeCount;
      runPreview();
    }

    function toISODate(d) {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    }

    function build52WeekCalendar() {
      const today = new Date();
      const dayOfWeek = today.getDay();
      
      const endSaturday = new Date(today);
      endSaturday.setDate(today.getDate() + (6 - dayOfWeek));

      const startSunday = new Date(endSaturday);
      startSunday.setDate(endSaturday.getDate() - (53 * 7 - 1));

      calendarDays = [];
      const monthsRow = document.getElementById("monthsRow");
      monthsRow.innerHTML = "";

      let curr = new Date(startSunday);
      let col = 0;
      let lastMonth = -1;
      let lastLeft = -50;
      const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

      while (curr <= endSaturday) {
        const dayIdx = curr.getDay();
        const dStr = curr.toISOString().split("T")[0];
        const m = curr.getMonth();

        if (m !== lastMonth) {
          let posLeft = col * 15.5;
          if (posLeft < lastLeft + 28) {
            posLeft = lastLeft + 28;
          }
          const mLabel = document.createElement("div");
          mLabel.className = "gh-month-label";
          mLabel.style.left = `${posLeft}px`;
          mLabel.textContent = monthNames[m];
          monthsRow.appendChild(mLabel);
          lastLeft = posLeft;
          lastMonth = m;
        }

        calendarDays.push({
          date: dStr,
          col: col,
          row: dayIdx,
          month: m
        });

        if (dayIdx === 6) col++;
        curr.setDate(curr.getDate() + 1);
      }
    }

    let clickSelectionPhase = 0;
    function handleCellClick(dStr) {
      const startEl = document.getElementById("startDate");
      const endEl = document.getElementById("endDate");

      if (clickSelectionPhase === 0) {
        startEl.value = dStr;
        endEl.value = dStr;
        clickSelectionPhase = 1;
        log(`Selected start: ${dStr}. Click another day to set end date.`, "info");
      } else {
        if (dStr < startEl.value) {
          endEl.value = startEl.value;
          startEl.value = dStr;
        } else {
          endEl.value = dStr;
        }
        clickSelectionPhase = 0;
        log(`Date range updated: ${startEl.value} to ${endEl.value}`, "info");
      }
      onDateInputChanged();
    }

    function renderCalendar() {
      const grid = document.getElementById("calendarGrid");
      grid.innerHTML = "";
      const startVal = document.getElementById("startDate").value;
      const endVal = document.getElementById("endDate").value;

      calendarDays.forEach(day => {
        const dStr = day.date;
        const exist = existingCommitsMap[dStr] || 0;
        const newlyAdded = simulatedCommitsMap[dStr] || 0;
        const total = exist + newlyAdded;

        let lvl = "lvl-0";
        if (total >= 1 && total <= 2) lvl = "lvl-1";
        else if (total >= 3 && total <= 5) lvl = "lvl-2";
        else if (total >= 6 && total <= 8) lvl = "lvl-3";
        else if (total >= 9) lvl = "lvl-4";

        const cell = document.createElement("div");
        cell.className = `day-cell ${lvl}`;

        if (startVal && endVal && dStr >= startVal && dStr <= endVal) {
          cell.style.outline = "1.5px solid rgba(88, 166, 255, 0.5)";
        }

        cell.onclick = () => handleCellClick(dStr);

        if (newlyAdded > 0) {
          cell.classList.add("is-new");
          cell.title = `${dStr}: ${exist} existing + ${newlyAdded} NEW commits (Click to select)`;
        } else {
          cell.title = `${dStr}: ${exist} contributions (Click to select)`;
        }

        grid.appendChild(cell);
      });
    }

    function validateCounts() {
      let min = parseInt(document.getElementById("minCommits").value) || 1;
      let max = parseInt(document.getElementById("maxCommits").value) || 1;
      if (min < 1) min = 1;
      if (max < min) max = min;
      document.getElementById("lblCommits").textContent = `${min} - ${max} commits`;
    }

    function updateLabels() {
      validateCounts();
      const freq = document.getElementById("freqSlider").value;
      document.getElementById("lblFreq").textContent = `${freq}%`;
    }

    function setPreset(preset, btnElement) {
      const today = new Date();
      if (preset === "past-year") {
        const past = new Date(today);
        past.setDate(today.getDate() - 364);
        document.getElementById("startDate").value = toISODate(past);
        document.getElementById("endDate").value = toISODate(today);
      } else if (preset === "past-6-months") {
        const past = new Date(today);
        past.setDate(today.getDate() - 180);
        document.getElementById("startDate").value = toISODate(past);
        document.getElementById("endDate").value = toISODate(today);
      } else if (preset === "past-3-months") {
        const past = new Date(today);
        past.setDate(today.getDate() - 90);
        document.getElementById("startDate").value = toISODate(past);
        document.getElementById("endDate").value = toISODate(today);
      } else if (preset === "current-month") {
        const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        document.getElementById("startDate").value = toISODate(startOfMonth);
        document.getElementById("endDate").value = toISODate(today);
      } else if (preset === "current-year") {
        const startOfYear = new Date(today.getFullYear(), 0, 1);
        document.getElementById("startDate").value = toISODate(startOfYear);
        document.getElementById("endDate").value = toISODate(today);
      }

      // Update button highlights
      document.querySelectorAll(".btn-preset").forEach(b => b.classList.remove("highlight"));
      if (btnElement) {
        btnElement.classList.add("highlight");
      } else {
        const targetBtn = document.querySelector(`.btn-preset[data-preset="${preset}"]`);
        if (targetBtn) targetBtn.classList.add("highlight");
      }

      document.getElementById("onlyEmptyDays").checked = true;
      runPreview();
    }

    function onDateInputChanged() {
      // Clear preset button highlight when custom dates are chosen
      document.querySelectorAll(".btn-preset").forEach(b => b.classList.remove("highlight"));
      runPreview();
    }

    function runPreview() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doRunPreview, 150);
    }

    async function doRunPreview() {
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      if (!start || !end) return;

      let minC = parseInt(document.getElementById("minCommits").value) || 2;
      let maxC = parseInt(document.getElementById("maxCommits").value) || 5;
      if (minC < 1) minC = 1;
      if (maxC < minC) maxC = minC;

      const freq = parseFloat(document.getElementById("freqSlider").value) / 100.0;
      const skipWk = document.getElementById("skipWeekends").checked;
      const onlyEmpty = document.getElementById("onlyEmptyDays").checked;

      try {
        const res = await fetch("/api/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            startDate: start,
            endDate: end,
            minCommits: minC,
            maxCommits: maxC,
            frequency: freq,
            skipWeekends: skipWk,
            onlyEmptyDays: onlyEmpty,
            existingMap: existingCommitsMap,
            commitPlan: simulatedCommitsMap
          })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        simulatedCommitsMap = data.commits_by_date || {};
        document.getElementById("statNewActive").textContent = data.active_days || 0;
        document.getElementById("statNewCommits").textContent = data.total_commits || 0;

        renderCalendar();
      } catch (err) {
        log("Preview error: " + err.message, "err");
      }
    }

    async function generateCommits() {
      const btn = document.getElementById("btnGenerate");
      const start = document.getElementById("startDate").value;
      const end = document.getElementById("endDate").value;
      if (!start || !end) {
        alert("Please select both start and end dates.");
        return;
      }

      let minC = parseInt(document.getElementById("minCommits").value) || 2;
      let maxC = parseInt(document.getElementById("maxCommits").value) || 5;
      if (minC < 1) minC = 1;
      if (maxC < minC) maxC = minC;

      const freq = parseFloat(document.getElementById("freqSlider").value) / 100.0;
      const skipWk = document.getElementById("skipWeekends").checked;
      const onlyEmpty = document.getElementById("onlyEmptyDays").checked;

      const confirmMsg = `Generate commits between ${start} and ${end} (Smart gap fill: ${onlyEmpty})?`;
      if (!confirm(confirmMsg)) return;

      btn.disabled = true;
      btn.textContent = "⏳ Generating...";
      log(`Starting backfill from ${start} to ${end}...`, "info");

      try {
        const res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            startDate: start,
            endDate: end,
            minCommits: minC,
            maxCommits: maxC,
            frequency: freq,
            skipWeekends: skipWk,
            onlyEmptyDays: onlyEmpty,
            existingMap: existingCommitsMap,
            commitPlan: simulatedCommitsMap
          })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        log(`Successfully created ${data.total_commits} commits across ${data.active_days} active days!`, "info");
        log("Click '⬆️ Push to GitHub' (top right) to synchronize your GitHub profile.", "info");

        for (let [d, count] of Object.entries(simulatedCommitsMap)) {
          if (count > 0) {
            existingCommitsMap[d] = (existingCommitsMap[d] || 0) + count;
          }
        }
        simulatedCommitsMap = {};
        document.getElementById("statNewActive").textContent = "0";
        document.getElementById("statNewCommits").textContent = "0";
        document.getElementById("statExistingDays").textContent = Object.values(existingCommitsMap).filter(c => c > 0).length;

        renderCalendar();
        await loadGitInfo();
      } catch (err) {
        log("Generation failed: " + err.message, "err");
      } finally {
        btn.disabled = false;
        btn.textContent = "🚀 Generate Commits";
      }
    }

    async function pushToGitHub() {
      const btn = document.getElementById("btnPush");
      btn.disabled = true;
      btn.textContent = "⏳ Pushing...";
      log("Pushing to remote repository...", "info");

      try {
        const res = await fetch("/api/push", { method: "POST" });
        const data = await res.json();
        if (!data.success) {
          log("Push error: " + (data.error || "Unknown error"), "err");
        } else {
          log("Pushed successfully!\\n" + (data.output || "Done."), "info");
        }
        await loadGitInfo();
      } catch (err) {
        log("Push request failed: " + err.message, "err");
      } finally {
        btn.disabled = false;
        btn.textContent = "⬆️ Push to GitHub";
      }
    }

    window.onload = async () => {
      build52WeekCalendar();
      setPreset('past-year');
      updateLabels();
      await loadGitInfo();
      await loadExistingCommits();
      await doRunPreview();
    };
  </script>
</body>
</html>
"""


class BackfillRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/info":
            info = get_git_info()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode("utf-8"))
        elif parsed.path == "/api/existing_commits":
            existing = get_existing_commits()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(existing).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if parsed.path == "/api/preview":
            try:
                res = simulate_backfill(
                    data.get("startDate"),
                    data.get("endDate"),
                    data.get("minCommits", 2),
                    data.get("maxCommits", 5),
                    float(data.get("frequency", 0.85)),
                    bool(data.get("skipWeekends", False)),
                    bool(data.get("onlyEmptyDays", True)),
                    data.get("existingMap"),
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/generate":
            try:
                res = execute_backfill(
                    data.get("startDate"),
                    data.get("endDate"),
                    data.get("minCommits", 2),
                    data.get("maxCommits", 5),
                    float(data.get("frequency", 0.85)),
                    bool(data.get("skipWeekends", False)),
                    bool(data.get("onlyEmptyDays", True)),
                    data.get("existingMap"),
                    data.get("commitPlan"),
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif parsed.path == "/api/push":
            res = execute_push()
            self.send_response(200 if res.get("success") else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server():
    server_address = ("127.0.0.1", PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, BackfillRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n=======================================================")
        print(f"  GitHub Contribution Backfiller UI running!")
        print(f"  Open in your browser: {url}")
        print(f"  Press Ctrl+C to stop the server.")
        print(f"=======================================================\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    run_server()
