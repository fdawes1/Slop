#!/usr/bin/env python3
"""
yt-agent — fully autonomous YouTube channel management

Usage:
  python run.py run                          # full pipeline: research → script → video → upload
  python run.py run --topic "AI agents"     # skip topic selection, use this topic
  python run.py run --dry-run               # full pipeline without uploading
  python run.py run --resume <RUN_ID>       # resume a failed/interrupted run
  python run.py schedule                    # run on automatic daily schedule
  python run.py schedule --run-now          # schedule + run immediately
  python run.py calendar                    # generate 7-day content calendar
  python run.py calendar --days 30          # generate 30-day calendar
  python run.py analytics                   # show channel performance
  python run.py analytics --refresh         # fetch fresh data from YouTube API
  python run.py runs                        # list recent pipeline runs
  python run.py auth                        # authenticate with YouTube (run once)
"""
from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

load_dotenv()
console = Console()


def load_config():
    channel_config = yaml.safe_load(Path("config/channel.yaml").read_text())
    settings = yaml.safe_load(Path("config/settings.yaml").read_text())
    return channel_config, settings


def get_env() -> dict:
    env = {}
    missing = []
    for key in ["ANTHROPIC_API_KEY"]:
        val = os.getenv(key)
        if not val:
            missing.append(key)
        env[key] = val or ""

    for key in ["OPENAI_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "STABILITY_API_KEY"]:
        env[key] = os.getenv(key, "")

    if missing:
        console.print(f"[red]Missing required env vars: {', '.join(missing)}[/red]")
        console.print("[dim]Copy .env.example to .env and add your API keys.[/dim]")
        sys.exit(1)

    return env


def cmd_run(args):
    channel_config, settings = load_config()
    env = get_env()
    from pipeline.orchestrator import run_pipeline

    state = run_pipeline(
        channel_config=channel_config,
        settings=settings,
        env=env,
        topic_override=args.topic,
        dry_run=args.dry_run,
        resume_run_id=args.resume,
    )
    console.print(f"\n[bold green]Done.[/bold green] Run ID: [dim]{state.run_id}[/dim]")


def cmd_schedule(args):
    import schedule as sched
    import time

    channel_config, settings = load_config()
    upload_time = channel_config["channel"]["upload_schedule"].get("time", "14:00")
    console.print(f"[cyan]Scheduling daily upload at {upload_time}[/cyan]")

    def job():
        console.rule("[bold]Scheduled Upload")
        env = get_env()
        from pipeline.orchestrator import run_pipeline
        try:
            run_pipeline(channel_config=channel_config, settings=settings, env=env)
        except Exception as e:
            console.print(f"[red]Scheduled run failed: {e}[/red]")

    sched.every().day.at(upload_time).do(job)

    if args.run_now:
        job()

    console.print(f"[green]Scheduler active. Ctrl+C to stop.[/green]")
    while True:
        sched.run_pending()
        time.sleep(30)


def cmd_analytics(args):
    channel_config, settings = load_config()
    env = get_env()
    from agents.analytics_agent import refresh_analytics, get_performance_summary

    if args.refresh:
        console.print("[cyan]Refreshing from YouTube API...[/cyan]")
        refresh_analytics(env, settings["paths"]["data"])

    summary = get_performance_summary(settings["paths"]["data"])

    console.print(Panel(
        f"Total Videos: [bold]{summary['total_videos']}[/bold]\n"
        f"Total Views:  [bold]{summary['total_views']:,}[/bold]\n"
        f"Avg Views:    [bold]{summary['avg_views']:,}[/bold]\n"
        f"Last Upload:  [dim]{summary.get('last_upload', 'N/A')}[/dim]",
        title="Channel Analytics",
    ))

    if summary.get("top_videos"):
        t = Table(title="Top Videos")
        t.add_column("Title", max_width=60)
        t.add_column("Views", justify="right")
        t.add_column("YouTube ID")
        for v in summary["top_videos"]:
            t.add_row(v["title"], f"{v['views']:,}", v.get("id") or "-")
        console.print(t)


def cmd_calendar(args):
    channel_config, settings = load_config()
    env = get_env()
    import anthropic
    from agents.strategy_agent import generate_content_calendar

    client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
    calendar = generate_content_calendar(channel_config, client, days=args.days)

    t = Table(title=f"{args.days}-Day Content Calendar")
    t.add_column("Day", width=4, justify="right")
    t.add_column("Topic", max_width=45)
    t.add_column("Angle", max_width=40)
    t.add_column("Type", width=12)
    t.add_column("Pillar", max_width=25)

    for entry in calendar:
        t.add_row(
            str(entry.get("day", "")),
            entry.get("topic", "")[:45],
            entry.get("angle", "")[:40],
            entry.get("content_type", ""),
            entry.get("pillar", "")[:25],
        )
    console.print(t)


def cmd_runs(args):
    _, settings = load_config()
    from pipeline.state import list_runs

    runs = list_runs(settings["paths"]["data"])
    if not runs:
        console.print("[yellow]No runs found.[/yellow]")
        return

    t = Table(title="Pipeline Runs")
    t.add_column("Run ID", width=10)
    t.add_column("Topic", max_width=45)
    t.add_column("Status", width=18)
    t.add_column("Created", width=19)
    t.add_column("YouTube ID", width=14)

    for r in runs[:25]:
        status_color = {
            "complete": "green", "uploaded": "green",
            "failed": "red", "dry_run_complete": "yellow",
        }.get(r["status"], "white")
        t.add_row(
            r["run_id"],
            r["topic"][:45],
            f"[{status_color}]{r['status']}[/{status_color}]",
            r["created_at"][:19],
            r.get("youtube_id") or "-",
        )
    console.print(t)


def cmd_auth(args):
    from tools.youtube_api import get_youtube_client
    console.print("[cyan]Opening browser for YouTube authentication...[/cyan]")
    get_youtube_client("client_secrets.json")
    console.print("[green]Authenticated. Token saved to data/youtube_token.pkl[/green]")


def main():
    p = argparse.ArgumentParser(
        description="yt-agent: autonomous YouTube channel management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    run_p = sub.add_parser("run", help="Run the full pipeline once")
    run_p.add_argument("--topic", help="Override topic selection")
    run_p.add_argument("--dry-run", action="store_true", help="Generate video without uploading")
    run_p.add_argument("--resume", metavar="RUN_ID", help="Resume an incomplete run")

    sched_p = sub.add_parser("schedule", help="Run on automatic daily schedule")
    sched_p.add_argument("--run-now", action="store_true", help="Also run immediately")

    anal_p = sub.add_parser("analytics", help="View channel analytics")
    anal_p.add_argument("--refresh", action="store_true", help="Fetch fresh data from YouTube")

    cal_p = sub.add_parser("calendar", help="Generate content calendar")
    cal_p.add_argument("--days", type=int, default=7, metavar="N", help="Number of days (default: 7)")

    sub.add_parser("runs", help="List recent pipeline runs")
    sub.add_parser("auth", help="Authenticate with YouTube (run once per machine)")

    args = p.parse_args()

    commands = {
        "run": cmd_run,
        "schedule": cmd_schedule,
        "analytics": cmd_analytics,
        "calendar": cmd_calendar,
        "runs": cmd_runs,
        "auth": cmd_auth,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
