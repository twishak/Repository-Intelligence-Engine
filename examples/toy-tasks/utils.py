"""Small helpers shared across the toy task manager."""


def format_task_line(title: str, done: bool) -> str:
    """Render a single task as a checklist line."""
    marker = "x" if done else " "
    return f"[{marker}] {title}"


def slugify(title: str) -> str:
    """Turn a task title into a short id-friendly slug."""
    return title.strip().lower().replace(" ", "-")
