import sys
import os
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from gscrub import __version__
from gscrub.scanner import Scanner, FileTarget
from gscrub.analyzer import Analyzer, AnalysisResult, RiskLevel
from gscrub.safety import Safety, BackupInfo
from gscrub.scrubber import Scrubber, ScrubResult


console = Console()


def is_interactive() -> bool:
    return os.isatty(sys.stdout.fileno()) and os.isatty(sys.stdin.fileno())


def print_header():
    console.print(Panel.fit(
        "[bold cyan]GitScrubbin — Git Safety Guardian[/bold cyan]\n"
        "[dim]Detect accidental exposures. Scrub safely. No regrets.[/dim]",
        border_style="cyan"
    ))


def print_help_panel():
    console.print(Panel.fit(
        "[bold]What GitScrubbin Does[/bold]\n\n"
        "[cyan]1. SCAN[/cyan] — Finds all files ever committed to your repo\n"
        "[cyan]2. ANALYZE[/cyan] — Checks each file for sensitive patterns\n"
        "[cyan]3. SHOW[/cyan] — Displays risk levels and history depth\n"
        "[cyan]4. SCRUB[/cyan] — Removes files from Git history permanently\n\n"
        "[bold]Understanding the Output[/bold]\n\n"
        "[yellow]Status: deleted[/yellow] = File was committed in the past but "
        "has since been removed from your working directory. It still exists "
        "in your Git history!\n\n"
        "[yellow]Status: tracked[/yellow] = File currently exists in your working directory\n\n"
        "[bold]Risk Levels[/bold]\n"
        "  [red]CRITICAL[/red] = Private keys, credentials, tokens, secrets\n"
        "  [yellow]HIGH[/yellow] = Env files, AWS keys, API tokens\n"
        "  [blue]MEDIUM[/blue] = Config files, scripts, old code\n"
        "  [green]LOW[/green] = Temp files, cache, builds\n\n"
        "[bold]Common Commands[/bold]\n\n"
        "  [cyan]gitscrubbin[reset]           # Interactive mode (shows all scrubbable files)\n"
        "  [cyan]gitscrubbin -v[reset]          # Verbose (show all files, not just risky ones)\n"
        "  [cyan]gitscrubbin -f .env[reset]     # Scrub specific file(s)\n"
        "  [cyan]gitscrubbin -n[reset]          # Dry run (preview only)\n"
        "  [cyan]gitscrubbin -y[reset]          # Auto-confirm (skip confirmation)\n"
        "  [cyan]gitscrubbin --help[reset]       # Show this help\n\n"
        "[bold]Example Workflow[/bold]\n\n"
        "[dim]# 1. Scan and see what files are in history[dim]\n"
        "$ gitscrubbin\n\n"
        "[dim]# 2. Preview what will happen (dry run)[dim]\n"
        "$ gitscrubbin -f .env -n\n\n"
        "[dim]# 3. Actually scrub (creates backup branch first)[dim]\n"
        "$ gitscrubbin -f .env -y\n\n"
        "[dim]# 4. Force push to remote[dim]\n"
        "$ git push --force --all\n"
        "$ git push --force --tags",
        title="[bold cyan]HELP[/bold cyan]",
        border_style="cyan"
    ))


def print_target_table(results):
    table = Table(title="[bold]Scrubbable Targets[/bold]", expand=True)
    table.add_column("File", style="cyan")
    table.add_column("Risk", style="white")
    table.add_column("Status", style="white")
    table.add_column("History", justify="right")

    for r in results:
        if r.risk_level == RiskLevel.CRITICAL:
            risk_style = "[red]CRITICAL[/red]"
        elif r.risk_level == RiskLevel.HIGH:
            risk_style = "[yellow]HIGH[/yellow]"
        elif r.risk_level == RiskLevel.MEDIUM:
            risk_style = "[blue]MEDIUM[/blue]"
        else:
            risk_style = "[green]LOW[/green]"

        if not r.target.exists_in_worktree:
            status = "[dim]deleted[/dim]"
        else:
            status = "[green]tracked[/green]"

        history = f"{r.target.commit_count} commits"
        table.add_row(r.target.path, risk_style, status, history)

    console.print(table)


def print_impact_analysis(files, total_commits):
    console.print(Panel.fit(
        f"[bold]Impact Analysis[/bold]\n\n"
        f"Files selected: {len(files)}\n"
        f"Commits affected: {total_commits}\n\n"
        f"[yellow]⚠ This will rewrite Git history![/yellow]",
        border_style="yellow"
    ))


def get_selection_cli(results, file_list):
    if file_list:
        return [f for f in file_list if any(r.target.path == f for r in results)]
    return [r.target.path for r in results if r.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)]


def confirm_scrub_cli(selected, backup):
    console.print("\n[bold]Files to scrub:[/bold]")
    for f in selected:
        console.print(f"  [red]•[/red] {f}")
    console.print(f"\n[dim]Backup branch: {backup.branch_name}[/dim]\n")


def run_scrub(selected, scrubber, results):
    targets = [r.target for r in results if r.target.path in selected]
    
    console.print("\n[bold cyan]🧼 Scrubbing...[/bold cyan]\n")
    
    for i, target in enumerate(targets):
        console.print(f"  [cyan]{i+1}.[/cyan] {target.path}")
    
    scrubber.scrub(targets)
    
    console.print("\n[bold green]✅ Scrub complete![/bold green]\n")


def print_next_steps(backup):
    console.print(Panel.fit(
        "[bold green]Next Steps[/bold green]\n\n"
        "Force push to update remote:\n"
        f"  [cyan]git push --force --all[/cyan]\n"
        f"  [cyan]git push --force --tags[/cyan]\n\n"
        f"Recovery: [dim]git checkout {backup.branch_name}[/dim]",
        border_style="green"
    ))


@click.command()
@click.option("-v", "--verbose", is_flag=True, help="Show all files, not just scrubbable")
@click.option("-n", "--dry-run", is_flag=True, help="Preview only, don't scrub")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@click.option("-f", "--files", default="", help="Files to scrub (comma-separated)")
@click.option("-h", "--help", "show_help", is_flag=True, help="Show help and exit")
def main(verbose, dry_run, yes, files, show_help):
    if show_help:
        print_header()
        print_help_panel()
        raise SystemExit(0)
    
    print_header()
    
    try:
        scanner = Scanner(".")
        scanner.git_root()
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
    safety = Safety(".")
    scrubber = Scrubber(".", safety)
    analyzer = Analyzer(scanner)
    
    console.print("\n[cyan]Scanning repository...[/cyan]\n")
    targets = scanner.scan()
    console.print(f"  Found {len(targets)} potential targets")
    
    if not targets:
        console.print("[green]✓ No files found — repository looks clean[/green]")
        raise SystemExit(0)
    
    console.print("[cyan]Analyzing risk...[/cyan]\n")
    results = analyzer.analyze_all(targets)
    
    if not verbose:
        results = [r for r in results if r.is_scrubbable]
    
    if not results:
        console.print("[green]✓ No scrubbable files found[/green]")
        raise SystemExit(0)
    
    print_target_table(results)
    
    file_list = [f.strip() for f in files.split(",") if f.strip()] if files else []
    selected = get_selection_cli(results, file_list)
    
    if not selected:
        console.print("[yellow]No files selected[/yellow]")
        raise SystemExit(0)
    
    selected_results = [r for r in results if r.target.path in selected]
    total_commits = sum(r.target.commit_count for r in selected_results)
    print_impact_analysis(selected, total_commits)
    
    if dry_run:
        console.print("\n[yellow]Dry run — no changes made[/yellow]")
        raise SystemExit(0)
    
    backup = safety.create_backup_branch(selected)
    console.print(f"[dim]Created backup branch: {backup.branch_name}[/dim]")
    
    if not yes:
        confirm_scrub_cli(selected, backup)
        console.print("[yellow]Run with -y to confirm[/yellow]")
        raise SystemExit(0)
    
    run_scrub(selected, scrubber, results)
    
    print_next_steps(backup)


if __name__ == "__main__":
    main()