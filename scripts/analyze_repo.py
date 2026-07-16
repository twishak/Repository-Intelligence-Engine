import argparse
import logging

from rich.console import Console
from rich.logging import RichHandler

from codebase_agent.insights import (
    AnalysisRunner,
    FindingCategory,
    FindingSeverity,
    RepositoryReport,
)
from codebase_agent.knowledge import KnowledgeBaseRegistry, RepoNotIngestedError

_SEVERITY_COLOR = {
    FindingSeverity.INFO: "dim",
    FindingSeverity.WARNING: "yellow",
    FindingSeverity.ERROR: "red",
}


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(show_path=False)],
    )
    console = Console()

    try:
        kb = KnowledgeBaseRegistry().get(args.repo)
    except RepoNotIngestedError as e:
        raise SystemExit(str(e)) from e

    report = AnalysisRunner().run(kb)
    _render(report, console, category=args.category)


def _render(report: RepositoryReport, console: Console, category: str | None) -> None:
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
        report.by_category(_parse_category(category)) if category else list(report)
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


def _parse_category(value: str) -> FindingCategory:
    try:
        return FindingCategory(value)
    except ValueError:
        raise SystemExit(
            f"Unknown category '{value}'. Choose from: {', '.join(c.value for c in FindingCategory)}"
        ) from None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Repository Insights analyzers over an ingested repository."
    )
    parser.add_argument("repo", help="Name of the ingested repository.")
    parser.add_argument(
        "--category",
        help="Only show findings in this category (dead_code, circular_dependency, complexity, todo, architecture).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
