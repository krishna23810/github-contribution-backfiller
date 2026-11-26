# GitHub Contribution Backfiller 🟩

A lightweight, cross-platform tool with an interactive Web UI and CLI to backfill and manage your GitHub contribution graph with realistic, natural commit patterns.

Zero external dependencies required — runs out-of-the-box with standard Python.

---

## ✨ Features

- **🟩 52-Week Live Contribution Calendar**: Exact replica of GitHub's contribution heat map layout (53 weeks × 7 days, Sunday–Saturday alignment, weekday labels `Mon`, `Wed`, `Fri`, and calibrated month headers).
- **🎯 Smart Gap Fill**: Intelligently identifies and populates only empty (0-contribution) days while preserving your existing active green days.
- **🔄 Live GitHub Profile Sync**: Fetches public contribution records directly for any GitHub username so your existing commits across all repositories appear on the graph.
- **⚡ Customizable Intensity & Pattern**:
  - Min and Max commits per day (e.g. 2–5 commits/day)
  - Activity rate slider (e.g. 85% probability for natural variation)
  - Optional weekend skipping (Saturdays & Sundays)
- **🖥️ Clean Side-by-Side Web UI**: Adjust date ranges and intensity on the left while previewing your updated graph in real-time on the right.
- **🚀 One-Click Commit & Push**: Generate past-dated commits and push them to your GitHub default branch (`main`) with a single click.
- **💻 CLI Script Included**: Full headless command-line interface via `backfill.py` with `--dry-run` simulation mode.
- **🌐 100% Dynamic & Shareable**: Automatically detects your local Git user and email with zero hardcoded credentials.

---

## 📖 User Guide & How to Use

### 1. Prerequisites
Ensure you have **Python 3.8+** and **Git** installed on your system.

```bash
python --version
git --version
```

Make sure your local Git configuration has the same email address that is linked and verified on your GitHub account:
```bash
git config --global user.name "YourGitHubUsername"
git config --global user.email "your_email@example.com"
```

---

### 2. Running the Web UI (Recommended)

#### On Windows:
Double-click:
```
start_ui.bat
```
*or in PowerShell / Command Prompt:*
```powershell
python app.py
```

#### On macOS / Linux:
```bash
chmod +x start_ui.sh
./start_ui.sh
# or: python3 app.py
```

The application will automatically open in your default browser at:
```
http://localhost:8765
```

---

### 3. Step-by-Step UI Walkthrough

```
┌───────────────────────────────────────┬──────────────────────────────────────────────┐
│  LEFT PANEL: Controls                 │  RIGHT PANEL: Live 52-Week Preview           │
├───────────────────────────────────────┼──────────────────────────────────────────────┤
│ 1. Select Date Range (Presets/Custom) │  [Nov  Dec  Jan  Feb  Mar  Apr  May ...]     │
│    ☑ Smart Gap Fill (Skip active days)│  Mon 🟩 🟩 🟩 🟩 🟦 🟦 🟦 🟩 🟩 🟩           │
│                                       │  Wed 🟩 🟩 🟩 🟩 🟦 🟦 🟦 🟩 🟩 🟩           │
│ 2. Intensity & Frequency Sliders      │  Fri 🟩 🟩 🟩 🟩 🟦 🟦 🟦 🟩 🟩 🟩           │
│    - Commits/Day: 2 - 5               │                                              │
│    - Activity Rate: 85%               │  (Solid green = Existing GitHub activity)    │
│    - ☐ Skip weekends                  │  (Blue border = New proposed commits)        │
│                                       ├──────────────────────────────────────────────┤
│ [ 🚀 Generate Commits ]               │ 📋 Activity Console & Live Logs              │
└───────────────────────────────────────┴──────────────────────────────────────────────┘
```

1. **Verify Your User**:
   Look at the header. If your GitHub handle is different from your local Git name, click **`[edit]`** next to your username to load your profile graph.
2. **Choose a Date Range**:
   - Use quick presets like **Current Month**, **Past 3 Months**, **Past 6 Months**, **Past 1 Year**, **Current Year (YTD)**, or select custom **Start Date** and **End Date**.
   - Keep **Smart Gap Fill** checked so it only commits to empty days without overwriting days you already worked on.
3. **Adjust Intensity**:
   - **Min / Max Commits**: Sets the range of commits per active day (higher commits create darker green squares).
   - **Activity Rate**: Percentage of days that receive commits (e.g., 85% for a natural look with occasional rest days).
   - **Skip Weekends**: Check this if you prefer a strict Monday–Friday work schedule.
4. **Preview**:
   Examine the 52-week calendar on the right. New commits are highlighted with a glowing blue border.
5. **Commit & Push**:
   - Click **`🚀 Generate Commits`**.
   - Click **`⬆️ Push to GitHub`** (top right) to synchronize with your GitHub account.

---

### 4. Running via Command Line (CLI)

For servers, headless environments, or automation scripts, use `backfill.py`:

#### A. Preview first without making commits (`--dry-run`):
```powershell
python backfill.py --start 2026-05-01 --end 2026-07-31 --dry-run
```

#### B. Fill a specific date range:
```powershell
python backfill.py --start 2026-05-01 --end 2026-07-31 --min 2 --max 5 --frequency 0.85
```

#### C. Push commits to GitHub:
```powershell
git push origin main
```

#### CLI Flag Reference:
| Flag | Description | Default |
|---|---|---|
| `--start` | Start date in `YYYY-MM-DD` format | *(Required)* |
| `--end` | End date in `YYYY-MM-DD` format | *(Required)* |
| `--min` | Minimum commits per active day | `1` |
| `--max` | Maximum commits per active day | `4` |
| `--frequency` | Probability of committing on each day (`0.0` to `1.0`) | `0.85` |
| `--skip-weekends` | Skip Saturday and Sunday commits | `False` |
| `--dry-run` | Simulate commits without writing to Git history | `False` |

---

## ⚙️ How It Works Under the Hood

### Git Backdating Mechanics
GitHub parses author and committer timestamps from each Git commit object:
1. **Timestamp Matching**: The script sets both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` environment variables to the target historical timestamp in ISO format:
   ```bash
   GIT_AUTHOR_DATE="2026-05-15T14:30:00"
   GIT_COMMITTER_DATE="2026-05-15T14:30:00"
   ```
2. **File Mutation**: Timestamps are written to `activity.txt` ensuring every commit has an authentic file diff (GitHub often skips `--allow-empty` commits).
3. **Identity Verification**: Uses your configured Git email (`git config user.email`), ensuring attribution to your profile.

---

## 📁 Repository Structure

```
github-contribution-backfiller/
├── app.py           # Web UI server & API (Python standard library, zero dependencies)
├── backfill.py      # Standalone CLI backfill script
├── start_ui.bat     # Windows launcher (double-click to start)
├── start_ui.sh      # macOS / Linux launcher script
├── activity.txt     # Log file updated by backdated commits
├── .gitignore       # Ignores Python bytecode and temporary files
└── README.md        # Documentation
```

---

## ❓ Troubleshooting & FAQs

### Why aren't my contributions showing up on GitHub?
1. **Email mismatch**: Ensure your local Git email (`git config user.email`) is added and verified in your [GitHub Email Settings](https://github.com/settings/emails).
2. **Default branch**: Commits only count if pushed to your repository's default branch (`main` or `master`).
3. **Private repository**: If your repo is private, enable **"Include private contributions on my profile"** in your GitHub profile settings.
4. **Processing delay**: GitHub usually takes **1 to 5 minutes** to rebuild your contribution graph after a push.

### How can others use this repository?
Anyone can fork or clone this repository, run `python app.py`, and backfill their own contributions. The app automatically detects their Git user and email with zero setup.
