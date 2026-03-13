"""
run.py — Prism CLI entry point

Usage:
  python run.py optimize -c "Google" -r "Senior ML Engineer" -j google_jd.txt
  python run.py status
  python run.py update --company "Google" --role "Senior ML Engineer" --status "Interviewing"
"""

import json
import os
from datetime import datetime
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

load_dotenv()

app     = typer.Typer(help="Prism — AI Resume Optimizer by Krishna Annavaram")
console = Console()

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI"
)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 1: optimize
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def optimize(
    company:  str  = typer.Option(..., "--company", "-c", help="Company name"),
    role:     str  = typer.Option(..., "--role",    "-r", help="Job role/title"),
    jd:       str  = typer.Option(..., "--jd",      "-j", help="Path to JD .txt file OR raw JD text"),
    thread:   str  = typer.Option("",  "--thread",        help="Thread ID to resume an existing run"),
    job_url:  str  = typer.Option("",  "--url",           help="Job posting URL (optional)"),
    no_hitl:  bool = typer.Option(False, "--no-hitl",     help="Skip human review checkpoint"),
):
    """Optimize Krishna's resume for a specific job, then log to Google Sheets."""
    from core.graph import compile_graph
    from core.tracker import log_application

    # ── Banner ────────────────────────────────────────────────────────────
    console.print(Panel(
        "[bold blue]PRISM[/bold blue] — AI Resume Optimizer\n"
        f"Target: [bold]{role}[/bold] @ [bold]{company}[/bold]",
        border_style="blue",
        expand=False,
    ))

    # ── Load JD ───────────────────────────────────────────────────────────
    jd_path = Path(jd)
    if jd_path.exists():
        jd_text = jd_path.read_text(encoding="utf-8")
        console.print(f"[dim]JD loaded from: {jd}[/dim]")
    else:
        jd_text = jd  # Treat --jd value as raw text
        console.print("[dim]JD provided as raw text.[/dim]")

    # ── Thread ID ─────────────────────────────────────────────────────────
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    thread_id = thread or f"{company}_{role}_{ts}".replace(" ", "_")

    graph  = compile_graph(hitl=not no_hitl)
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "raw_jd":         jd_text,
        "company_name":   company,
        "role_name":      role,
        "job_url":        job_url,
        "salary_range":   "",
        "loop_count":     0,
        "human_approved": False,
        "human_feedback": "",
        "thread_id":      thread_id,
        "logs":           [],
        "errors":         [],
    }

    # ── Phase 1: Run until HITL interrupt ─────────────────────────────────
    console.print("\n[bold cyan]Phase 1 — AI Pipeline running...[/bold cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Pre-processing JD and loading resume...", total=None)

        try:
            result = graph.invoke(initial_state, config=config)
        except Exception as e:
            console.print(f"[red]Pipeline error: {e}[/red]")
            raise typer.Exit(1)

        progress.update(task, description="[green]✓ Phase 1 complete")

    score = result.get("critic_score", "N/A")
    draft = result.get("draft_resume", "")

    # ── Human Review Checkpoint ───────────────────────────────────────────
    if not no_hitl:
        console.print("\n")
        console.print(Panel(
            draft,
            title=f"[bold yellow]DRAFT RESUME — Critic Score: {score}/100[/bold yellow]",
            border_style="yellow",
        ))

        # Show errors if any
        errors = result.get("errors", [])
        if errors:
            console.print(f"\n[yellow]⚠ {len(errors)} warning(s) during pipeline:[/yellow]")
            for err in errors[-3:]:
                console.print(f"  [dim]{err.get('node','')}:[/dim] {err.get('error','')[:80]}")

        console.print("\n[bold]Review the draft above.[/bold]")
        console.print("  [dim]Press Enter or type 'y' to approve.[/dim]")
        console.print("  [dim]Type specific feedback to incorporate it.[/dim]")
        console.print("  [dim]Type 'n' to cancel.[/dim]")

        feedback = Prompt.ask("\n  Your response", default="y")

        if feedback.lower() == "n":
            console.print("[red]Cancelled.[/red]")
            raise typer.Exit()

        update: dict = {"human_approved": True}
        if feedback.lower() not in ("y", "yes", ""):
            update["human_feedback"]   = feedback
            update["reflection_notes"] = f"HUMAN FEEDBACK:\n{feedback}"
            update["critic_score"]     = 0  # Force one more rewriter pass
            console.print("[cyan]Feedback noted — running one more optimization pass...[/cyan]")

        # ── Phase 2: Quality gates + humanizer + cover letter ─────────────
        console.print("\n[bold cyan]Phase 2 — Quality gates, humanizer, cover letter...[/bold cyan]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            t = progress.add_task("Running final pipeline...", total=None)
            try:
                result = graph.invoke(update, config=config)
            except Exception as e:
                console.print(f"[red]Phase 2 error: {e}[/red]")
                raise typer.Exit(1)
            progress.update(t, description="[green]✓ All done!")
    else:
        # no_hitl: result already contains full run
        pass

    # ── Final Score Card ──────────────────────────────────────────────────
    report = result.get("ats_score_report", {})

    table = Table(
        title="PRISM — Final Score Card",
        border_style="blue",
        show_header=True,
        header_style="bold blue",
    )
    table.add_column("Metric",   style="bold", min_width=22)
    table.add_column("Value",    justify="right", min_width=20)

    kw_matched  = len(report.get("keywords_matched", []))
    kw_total    = kw_matched + len(report.get("keywords_missing", []))
    fact_icon   = "✅ PASS" if report.get("fact_check_passed") else "⚠️  VIOLATIONS"
    status_icon = "✅ PASS" if report.get("status") == "PASS" else "⚠️  NEEDS REVIEW"

    table.add_row("ATS Score",          f"{report.get('final_ats_score', 'N/A')}/100")
    table.add_row("Keyword Density",    f"{report.get('keyword_density_pct', 'N/A')}%")
    table.add_row("Keywords Matched",   f"{kw_matched}/{kw_total}")
    table.add_row("Fact Check",         fact_icon)
    table.add_row("Reflexion Loops",    str(report.get("reflexion_loops_used", "N/A")))
    table.add_row("Cover Letter Risk",  f"{report.get('cover_letter_ai_risk', 'N/A')}/100")
    table.add_row("Cover Letter Words", str(report.get("cover_letter_word_count", "N/A")))
    table.add_row("Overall Status",     status_icon)

    console.print("\n")
    console.print(table)

    resume_path = result.get("resume_output_path", "")
    cl_path     = result.get("cover_letter_path",  "")
    console.print(f"\n[green]Files saved:[/green]")
    console.print(f"  Resume:       [bold]{resume_path}[/bold]")
    console.print(f"  Cover Letter: [bold]{cl_path}[/bold]")

    # ── Application Tracker ───────────────────────────────────────────────
    console.print("\n" + "─" * 60)
    console.print("[bold]📋 APPLICATION TRACKER[/bold]")
    console.print("─" * 60)

    applied = Confirm.ask("Did you apply for this job?", default=False)

    if applied:
        status = "Applied"
        notes  = Prompt.ask("Any notes? (press Enter to skip)", default="")
        url    = Prompt.ask("Job URL? (press Enter to skip)", default=job_url)
    else:
        save_anyway = Confirm.ask("Save as 'To Apply' for future tracking?", default=True)
        if not save_anyway:
            console.print("[dim]Not logged.[/dim]")
            raise typer.Exit()
        status = "To Apply"
        notes  = Prompt.ask("Any notes? (press Enter to skip)", default="")
        url    = Prompt.ask("Job URL? (press Enter to skip)", default=job_url)

    console.print("[dim]Logging to Google Sheets...[/dim]")

    success = log_application(
        company           = company,
        role              = role,
        status            = status,
        ats_report        = report,
        resume_file       = resume_path,
        cover_letter_file = cl_path,
        thread_id         = thread_id,
        notes             = notes,
        job_url           = url,
        salary_range      = result.get("salary_range", ""),
    )

    if success:
        console.print(Panel(
            f"[bold green]✅ Logged to Google Sheets![/bold green]\n"
            f"Company: {company}  |  Role: {role}\n"
            f"Status: [bold]{status}[/bold]  |  "
            f"ATS Score: {report.get('final_ats_score', 'N/A')}/100",
            border_style="green",
            expand=False,
        ))
        console.print(f"\n[link={SHEET_URL}]📊 Open Google Sheet ↗[/link]")
    else:
        console.print("[yellow]⚠  Could not write to Google Sheets.[/yellow]")
        console.print("[yellow]   See credentials/README.md for setup.[/yellow]")

        # Local fallback
        Path("output").mkdir(exist_ok=True)
        fallback = {
            "company": company, "role": role, "status": status,
            "ats_score": report.get("final_ats_score"),
            "thread_id": thread_id, "timestamp": ts,
        }
        fallback_path = f"output/{thread_id}_tracker.json"
        Path(fallback_path).write_text(json.dumps(fallback, indent=2))
        console.print(f"[yellow]   Saved locally: {fallback_path}[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 2: status — view tracker dashboard
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def status():
    """View your job application dashboard from Google Sheets."""
    from core.tracker import get_application_stats

    console.print(Panel(
        "[bold blue]PRISM[/bold blue] — Application Dashboard",
        border_style="blue",
        expand=False,
    ))

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Fetching from Google Sheets...", total=None)
        stats = get_application_stats()
        p.update(t, description="[green]✓ Done")

    if "error" in stats:
        console.print(f"[red]Could not fetch data: {stats['error']}[/red]")
        console.print("[yellow]Check credentials/README.md for setup instructions.[/yellow]")
        raise typer.Exit(1)

    if stats.get("total", 0) == 0:
        console.print("[dim]No applications logged yet. Run 'python run.py optimize' to get started.[/dim]")
        raise typer.Exit()

    # Summary table
    summary = Table(title="Application Summary", border_style="blue")
    summary.add_column("Metric", style="bold")
    summary.add_column("Value",  justify="right")
    summary.add_row("Total Applications", str(stats["total"]))
    summary.add_row("Average ATS Score",  f"{stats.get('avg_ats_score', 'N/A')}/100")
    for s, count in stats.get("by_status", {}).items():
        summary.add_row(s, str(count))
    console.print(summary)

    # Recent applications
    recent = stats.get("recent", [])
    if recent:
        console.print("\n")
        rec_table = Table(title="Last 5 Applications", border_style="dim")
        for col in ["Company", "Role", "Status", "ATS Score", "Date Applied"]:
            rec_table.add_column(col)
        for row in recent:
            rec_table.add_row(
                str(row.get("Company", "")),
                str(row.get("Role", "")),
                str(row.get("Status", "")),
                str(row.get("ATS Score", "")),
                str(row.get("Date Applied", "")),
            )
        console.print(rec_table)

    console.print(f"\n[link={SHEET_URL}]📊 Open full Google Sheet ↗[/link]")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 3: update — update application status
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def update(
    company:    str = typer.Option(..., "--company", "-c", help="Company name"),
    role:       str = typer.Option(..., "--role",    "-r", help="Job role"),
    new_status: str = typer.Option(..., "--status",  "-s",
                                   help="New status: Applied|To Apply|Interviewing|Offer|Rejected|Ghosted"),
):
    """Update the status of an existing application in Google Sheets."""
    from core.tracker import update_application_status

    VALID = {"Applied", "To Apply", "Interviewing", "Offer", "Rejected", "Ghosted"}
    if new_status not in VALID:
        console.print(f"[red]Invalid status. Choose from: {', '.join(sorted(VALID))}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Updating {company} / {role} → {new_status}...[/dim]")
    ok = update_application_status(company, role, new_status)

    if ok:
        console.print(f"[green]✅ Updated: {company} — {role} → [bold]{new_status}[/bold][/green]")
        console.print(f"\n[link={SHEET_URL}]📊 Open Google Sheet ↗[/link]")
    else:
        console.print(f"[yellow]⚠  Row not found for {company} / {role}.[/yellow]")
        console.print("[yellow]   Check spelling or update the sheet manually.[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
