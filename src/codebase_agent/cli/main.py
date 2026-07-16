import logging

import typer
from rich.console import Console
from rich.logging import RichHandler

from codebase_agent.application import (
    ApplicationError,
    IngestionService,
    InsightsService,
    ReasoningService,
    RepositoryService,
)
from codebase_agent.insights import FindingCategory, FindingSeverity, RepositoryReport
from codebase_agent.knowledge import RepoMetadata
from codebase_agent.reasoning import ReasoningResult

app = typer.Typer(
    help="Repository Intelligence Engine - ingest a repo, then ask questions or run analysis."
)
console = Console()

_SEVERITY_COLOR = {
    FindingSeverity.INFO: "dim",
    FindingSeverity.WARNING: "yellow",
    FindingSeverity.ERROR: "red",
}


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(show_path=False)],
    )


@app.callback()
def main() -> None:
    _configure_logging()


@app.command()
def ingest(
    source: str = typer.Argument(
        ..., help="Local path or git URL of the repository to ingest."
    ),
) -> None:
    """Ingest a repository (local path or git URL)."""
    _run(lambda: _render_metadata(IngestionService().ingest_repository(source)))


@app.command(name="list")
def list_repositories() -> None:
    """List ingested repositories."""

    def _do() -> None:
        repos = RepositoryService().list_repositories()
        if not repos:
            console.print(
                "No repositories ingested yet. Run 'codebase-agent ingest <source>' first."
            )
        for repo in repos:
            console.print(repo)

    _run(_do)


@app.command()
def info(
    repo_name: str = typer.Argument(..., help="Name of the ingested repository."),
) -> None:
    """Show metadata for one ingested repository."""
    _run(lambda: _render_metadata(RepositoryService().get_repository(repo_name)))


@app.command()
def ask(
    repo_name: str = typer.Argument(..., help="Name of the ingested repository."),
    question: str = typer.Argument(..., help="The question to ask."),
    active_file: str | None = typer.Option(
        None, help="File the user is currently viewing, for grounding."
    ),
    active_symbol: str | None = typer.Option(
        None, help="Symbol the user is currently viewing, for grounding."
    ),
) -> None:
    """Ask a question about a repository, grounded in retrieved evidence."""

    def _do() -> None:
        result = ReasoningService().answer_question(
            repo_name, question, active_file=active_file, active_symbol=active_symbol
        )
        _render_answer(result)

    _run(_do)


@app.command()
def analyze(
    repo_name: str = typer.Argument(..., help="Name of the ingested repository."),
    category: str | None = typer.Option(
        None, help="Only show findings in this category."
    ),
) -> None:
    """Run the Repository Insights analyzers over a repository."""

    if category is not None and category not in {c.value for c in FindingCategory}:
        choices = ", ".join(c.value for c in FindingCategory)
        console.print(
            f"[red]Unknown category '{category}'. Choose from: {choices}[/red]"
        )
        raise typer.Exit(code=1)

    def _do() -> None:
        report = InsightsService().analyze_repository(repo_name)
        _render_report(report, category=category)

    _run(_do)


def _run(action) -> None:
    try:
        action()
    except ApplicationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1) from None


def _render_metadata(metadata: RepoMetadata) -> None:
    console.print(f"[bold]{metadata.repo_name}[/bold]")
    console.print(f"  source: {metadata.source}")
    console.print(f"  ingested_at: {metadata.ingested_at}")
    console.print(f"  files: {len(metadata.files)}")
    console.print(f"  symbols: {metadata.symbol_count}")
    console.print(f"  schema_version: {metadata.schema_version}")
    if metadata.summary:
        console.print(f"  summary: {metadata.summary}")


def _render_answer(result: ReasoningResult) -> None:
    console.print(f"[bold]{result.answer}[/bold]\n")
    console.print(
        f"confidence={result.confidence.value} evidence_sufficient={result.evidence_sufficient}"
    )

    if result.assumptions:
        console.print("[yellow]Assumptions:[/yellow]")
        for assumption in result.assumptions:
            console.print(f"  - {assumption}")

    if result.limitations:
        console.print("[yellow]Limitations:[/yellow]")
        for limitation in result.limitations:
            console.print(f"  - {limitation}")

    if result.citations:
        console.print("Citations:")
        for citation in result.citations:
            location = (
                f"{citation.file_path}:{citation.start_line}-{citation.end_line}"
                if citation.file_path
                else "(no location)"
            )
            console.print(
                f"  [{citation.evidence_index}] {citation.qualified_name or '(unnamed)'} ({location})"
            )

    if result.validation_issues:
        console.print("[red]Validation issues:[/red]")
        for issue in result.validation_issues:
            console.print(f"  [{issue.severity.value}] {issue.message}")


def _render_report(report: RepositoryReport, category: str | None) -> None:
    console.print(f"[bold]Repository Report: {report.metadata.repo_name}[/bold]")
    console.print(
        f"generated_at={report.generated_at} execution_time={report.execution_time_seconds:.2f}s"
    )
    console.print(f"analyzers_run={', '.join(report.analyzers_run)}\n")

    stats = report.statistics
    console.print("[bold]Statistics[/bold]")
    console.print(
        f"  files={stats.total_files} symbols={stats.total_symbols} "
        f"(functions={stats.function_count} methods={stats.method_count} classes={stats.class_count})"
    )
    console.print(
        f"  call_edges={stats.total_call_edges} (resolved={stats.resolved_call_edges}) "
        f"import_edges={stats.total_import_edges} (resolved={stats.resolved_import_edges}) "
        f"inherits_edges={stats.total_inherits_edges}\n"
    )

    console.print("[bold]Findings by category[/bold]")
    for finding_category, count in sorted(
        report.finding_counts().items(), key=lambda kv: kv[0].value
    ):
        console.print(f"  {finding_category.value}: {count}")
    console.print()

    findings = (
        report.by_category(FindingCategory(category)) if category else list(report)
    )
    console.print(f"[bold]Findings{f' ({category})' if category else ''}[/bold]")
    if not findings:
        console.print("  (none)")
    for finding in findings:
        color = _SEVERITY_COLOR[finding.severity]
        location = (
            f"{finding.file_path}:{finding.start_line}" if finding.file_path else ""
        )
        console.print(
            f"  [{color}][{finding.severity.value}][/{color}] {finding.title} {location}"
        )
        console.print(f"    {finding.description}")

    if report.warnings:
        console.print("\n[red]Analyzer warnings:[/red]")
        for warning in report.warnings:
            console.print(f"  [{warning.analyzer}] {warning.message}")


if __name__ == "__main__":
    app()
