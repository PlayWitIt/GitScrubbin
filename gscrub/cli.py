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
        "[bold cyan]gscrub — Git Safety Guardian[/bold cyan]\n"
        "[dim]Detect accidental exposures. Scrub safely. No regrets.[/dim]",
        border_style="cyan"
    ))


def print_help_panel():
    console.print(Panel.fit(
        "[bold]What GitScrubbin Does[/bold]\n\n"
        "[cyan]1. SCAN[/cyan] — Finds all files ever committed to your repo\n"
        "[cyan]2. CATEGORIZE[/cyan] — Groups files by risk level\n"
        "[cyan]3. SHOW[/cyan] — Displays what would be removed\n"
        "[cyan]4. SCRUB[/cyan] — Removes files from Git history permanently\n\n"
        "[bold]Understanding Risk Levels[/bold]\n\n"
        "[red]CRITICAL[/red] = SSH keys, certificates — MUST scrub NOW\n"
        "[yellow]HIGH[/yellow] = .env, tokens, credentials — SHOULD scrub\n"
        "[blue]MEDIUM[/blue] = Config files, code — user decides\n"
        "[green]LOW[/green] = Build artifacts — ignore (not risky)\n\n"
        "[bold]Understanding Status[/bold]\n\n"
        "[yellow]deleted[yellow] = Was committed, now removed from worktree\n"
        "                    Still exists in Git history!\n"
        "[green]tracked[green] = Currently exists in worktree\n\n"
        "[bold]Example Commands[/bold]\n\n"
        "  [cyan]gitscrubbin[reset]           # Scan and interact\n"
        "  [cyan]gitscrubbin -v[reset]          # Show all files (verbose)\n"
        "  [cyan]gitscrubbin -f .env[reset]     # Scrub specific file\n"
        "  [cyan]gitscrubbin -n[reset]          # Dry run preview\n"
        "  [cyan]gitscrubbin -y[reset]          # Auto-confirm\n"
        "  [cyan]gitscrubbin -h[reset]          # Show this help",
        title="[bold cyan]HELP[/bold cyan]",
        border_style="cyan"
    ))


def print_target_table(results):
    table = Table(title="[bold]Files in Git History[/bold]", expand=True)
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Risk", style="white")
    table.add_column("Status", style="white")
    table.add_column("Why", style="dim", no_wrap=False)
    table.add_column("Commits", justify="right")

    for r in results:
        if r.risk_level == RiskLevel.CRITICAL:
            risk_style = "[red]CRITICAL[/red]"
        elif r.risk_level == RiskLevel.HIGH:
            risk_style = "[yellow]HIGH[/yellow]"
        elif r.risk_level == RiskLevel.MEDIUM:
            risk_style = "[blue]MEDIUM[/blue]"
        elif r.risk_level == RiskLevel.LOW:
            risk_style = "[green]LOW[/green]"
        else:
            risk_style = "[dim]SAFE[/dim]"

        if not r.target.exists_in_worktree:
            status = "[dim]deleted[/dim]"
        else:
            status = "[green]tracked[/green]"

        history = f"{r.target.commit_count}"
        table.add_row(
            r.target.path,
            risk_style,
            status,
            r.explanation,
            history
        )

    console.print(table)


def print_impact_analysis(files, total_commits):
    console.print(Panel.fit(
        f"[bold]Impact Analysis[/bold]\n\n"
        f"Files to scrub: {len(files)}\n"
        f"Commits affected: {total_commits}\n\n"
        f"[yellow]⚠ This will rewrite Git history![/yellow]",
        border_style="yellow"
    ))


def get_selection_cli(results, file_list):
    if file_list:
        return [f for f in file_list if any(r.target.path == f for r in results)]
    # Default: select CRITICAL and HIGH only
    return [r.target.path for r in results if r.risk_level in (
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
    )]


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
    
    console.print("\n[bold green]✅ Done![/bold green]\n")


def print_next_steps(backup):
    console.print(Panel.fit(
        "[bold green]Next Steps[/bold green]\n\n"
        "Update remote with:\n"
        "  [cyan]git push --force --all[/cyan]\n"
        "  [cyan]git push --force --tags[/cyan]\n\n"
        "If something goes wrong, recover with:\n"
        "  [dim]git checkout {backup.branch_name}[/dim]",
        border_style="green"
    ))


@click.command()
@click.option("-v", "--verbose", is_flag=True, help="Show all files including LOW risk")
@click.option("-n", "--dry-run", is_flag=True, help="Preview only, don't scrub")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
@click.option("-f", "--files", default="", help="Files to scrub (comma-separated)")
@click.option("-h", "--help", "show_help", is_flag=True, help="Show help")
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
    console.print(f"  Found {len(targets)} files in history")
    
    if not targets:
        console.print("[green]✓ Repository is clean[/green]")
        raise SystemExit(0)
    
    # Analyze ALL files (not just scrubbable ones)
    results = analyzer.analyze_all_raw(targets)
    
    # Filter based on verbosity
    if not verbose:
        results = [r for r in results if r.is_scrubbable]
    
    if not results:
        console.print("[green]✓ No risky files found[/green]")
        raise SystemExit(0)
    
    # Sort by risk level (CRITICAL first)
    risk_order = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3,
        RiskLevel.SAFE: 4,
    }
    results.sort(key=lambda r: risk_order[r.risk_level])
    
    print_target_table(results)
    
    # Select files
    file_list = [f.strip() for f in files.split(",") if f.strip()] if files else []
    selected = get_selection_cli(results, file_list)
    
    # Check if there are any risky files
    has_critical = any(r.risk_level == RiskLevel.CRITICAL for r in results)
    has_high = any(r.risk_level == RiskLevel.HIGH for r in results)
    has_medium = any(r.risk_level == RiskLevel.MEDIUM for r in results)
    
    if not selected:
        if not (has_critical or has_high or has_medium):
            console.print("\n[green]✓ No risky files found![/green]")
            console.print("[dim]Your repository looks safe.[/dim]")
            raise SystemExit(0)
        
        console.print("\n[yellow]No CRITICAL or HIGH risk files found.[/yellow]")
        
        if has_medium:
            console.print(f"\n[dim]Found {sum(1 for r in results if r.risk_level == RiskLevel.MEDIUM)} MEDIUM risk files.[/dim]")
            console.print("[dim]These are old code/files - probably not secrets.[/dim]")
            console.print("[dim]Use -f filename to select specific files if you want to scrub them.[/dim]")
        
        raise SystemExit(0)
    
    selected_results = [r for r in results if r.target.path in selected]
    total_commits = sum(r.target.commit_count for r in selected_results)
    print_impact_analysis(selected, total_commits)
    
    if dry_run:
        console.print("\n[yellow]Dry run — nothing changed[/yellow]")
        raise SystemExit(0)
    
    # Create backup
    backup = safety.create_backup_branch(selected)
    console.print(f"[dim]Backup: {backup.branch_name}[/dim]")
    
    if not yes:
        confirm_scrub_cli(selected, backup)
        console.print("[cyan]Run with -y to confirm[/cyan]")
        raise SystemExit(0)
    
    run_scrub(selected, scrubber, results)
    print_next_steps(backup)


if __name__ == "__main__":
    main()