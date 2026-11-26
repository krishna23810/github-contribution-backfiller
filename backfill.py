#!/usr/bin/env python3
"""
Git Backfill Script
Creates commits with past dates to populate GitHub contribution graph.
"""

import argparse
import datetime
import os
import random
import subprocess
import sys


def parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")


def generate_commits(
    start_date: datetime.date,
    end_date: datetime.date,
    min_commits: int,
    max_commits: int,
    frequency: float,
    skip_weekends: bool,
    dry_run: bool,
    filename: str = "activity.txt",
):
    if start_date > end_date:
        print(f"Error: start_date ({start_date}) cannot be after end_date ({end_date}).", file=sys.stderr)
        sys.exit(1)

    current_date = start_date
    total_commits = 0
    total_days = (end_date - start_date).days + 1
    active_days = 0

    print(f"\n--- Backfill Configuration ---")
    print(f"Date Range    : {start_date} to {end_date} ({total_days} days)")
    print(f"Commits/Day   : {min_commits} - {max_commits}")
    print(f"Day Frequency : {int(frequency * 100)}%")
    print(f"Skip Weekends : {skip_weekends}")
    print(f"Dry Run       : {dry_run}")
    print(f"-------------------------------\n")

    env = os.environ.copy()

    while current_date <= end_date:
        # Check weekend
        is_weekend = current_date.weekday() >= 5
        if skip_weekends and is_weekend:
            current_date += datetime.timedelta(days=1)
            continue

        # Check random frequency
        if random.random() <= frequency:
            active_days += 1
            commits_count = random.randint(min_commits, max_commits)
            for i in range(commits_count):
                total_commits += 1
                # Random time between 09:00 and 21:00
                hour = random.randint(9, 21)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                commit_dt = datetime.datetime.combine(
                    current_date, datetime.time(hour, minute, second)
                )
                # ISO formatted date with local offset
                formatted_date = commit_dt.strftime("%Y-%m-%dT%H:%M:%S")

                if dry_run:
                    if total_commits <= 10 or current_date == end_date:
                        print(f"[Dry Run] Commit #{total_commits}: {formatted_date}")
                    elif total_commits == 11:
                        print(f"[Dry Run] ...")
                else:
                    env["GIT_AUTHOR_DATE"] = formatted_date
                    env["GIT_COMMITTER_DATE"] = formatted_date

                    with open(filename, "a", encoding="utf-8") as f:
                        f.write(f"Contribution on {formatted_date} - commit #{total_commits}\n")

                    subprocess.run(
                        ["git", "add", filename],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    msg = f"chore: update activity log {formatted_date}"
                    subprocess.run(
                        ["git", "commit", "-m", msg],
                        env=env,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

        current_date += datetime.timedelta(days=1)

    print(f"\n[Done] Summary:")
    print(f"- Total active days: {active_days}/{total_days}")
    print(f"- Total commits generated: {total_commits}")
    if dry_run:
        print("\nThis was a dry run. Run without --dry-run to apply commits.")
    else:
        print("\nCommits created successfully! Run 'git push origin main' to push to GitHub.")


def main():
    parser = argparse.ArgumentParser(description="Backfill Git contributions for past dates.")
    parser.add_argument(
        "--start",
        type=parse_date,
        required=True,
        help="Start date (YYYY-MM-DD), e.g. 2026-01-01",
    )
    parser.add_argument(
        "--end",
        type=parse_date,
        required=True,
        help="End date (YYYY-MM-DD), e.g. 2026-11-25",
    )
    parser.add_argument(
        "--min",
        type=int,
        default=1,
        help="Minimum commits per active day (default: 1)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=4,
        help="Maximum commits per active day (default: 4)",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=0.85,
        help="Probability of committing on each day (0.0 to 1.0, default: 0.85)",
    )
    parser.add_argument(
        "--skip-weekends",
        action="store_true",
        help="Skip committing on weekends (Saturday and Sunday)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the backfill without creating actual commits",
    )

    args = parser.parse_args()

    generate_commits(
        start_date=args.start,
        end_date=args.end,
        min_commits=args.min,
        max_commits=args.max,
        frequency=args.frequency,
        skip_weekends=args.skip_weekends,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
