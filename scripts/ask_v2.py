import argparse
import logging

from rich.console import Console
from rich.logging import RichHandler

from codebase_agent.knowledge import KnowledgeBaseRegistry, RepoNotIngestedError
from codebase_agent.reasoning import (
    ReasoningEngine,
    ReasoningResult,
    answer_question,
    build_reasoning_pipeline,
)
from codebase_agent.retrieval.executor import RetrievalExecutor
from codebase_agent.retrieval.planner import RetrievalPlanner

_EXIT_COMMANDS = {"exit", "quit", "q"}


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(show_path=False)],
    )
    console = Console()

    if args.list:
        for repo in KnowledgeBaseRegistry().list_repos():
            console.print(repo)
        return

    if not args.repo:
        raise SystemExit(
            "Missing repo name. Usage: python scripts/ask_v2.py <repo> [-q QUESTION]"
        )

    if args.question:
        _ask_once(args.repo, args.question, console)
    else:
        _run_repl(args.repo, console)


def _ask_once(repo_name: str, question: str, console: Console) -> None:
    try:
        result = answer_question(repo_name, question)
    except RepoNotIngestedError as e:
        raise SystemExit(str(e)) from e
    _render(result, console)


def _run_repl(repo_name: str, console: Console) -> None:
    console.print(
        f"Ask questions about [bold]{repo_name}[/bold] (reasoning engine, evidence-driven; "
        f"type 'exit' to quit)\n"
    )

    # Reused across turns so the LLM client, embedder, and KnowledgeBase are
    # only initialized once per session, not on every question.
    pipeline = build_reasoning_pipeline(
        RetrievalPlanner(),
        RetrievalExecutor(),
        ReasoningEngine(),
        KnowledgeBaseRegistry(),
    )

    while True:
        try:
            question = console.input("[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not question:
            continue
        if question.lower() in _EXIT_COMMANDS:
            break

        with console.status("reasoning..."):
            final_state = pipeline.invoke(
                {
                    "repo_name": repo_name,
                    "question": question,
                    "context": None,
                    "plan": None,
                    "evidence": None,
                    "result": None,
                }
            )
        _render(final_state["result"], console)
        console.print()


def _render(result: ReasoningResult, console: Console) -> None:
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

    console.print(
        f"[dim]model={result.model} prompt_version={result.prompt_version} "
        f"reasoning_time={result.reasoning_time_seconds:.2f}s "
        f"retrieval_time={result.evidence_bundle.execution_time_seconds:.2f}s[/dim]"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask questions using the evidence-driven reasoning engine (v2)."
    )
    parser.add_argument("repo", nargs="?", help="Name of the ingested repository.")
    parser.add_argument(
        "-q",
        "--question",
        help="Ask a single question and exit, instead of starting a REPL.",
    )
    parser.add_argument(
        "--list", action="store_true", help="List ingested repositories and exit."
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
