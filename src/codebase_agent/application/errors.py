class ApplicationError(Exception):
    """Base for every error the application-service layer raises.

    CLI and FastAPI catch this hierarchy exclusively - neither needs to know
    about RepoNotIngestedError, IncompatibleSchemaError, or any other
    lower-layer exception type directly.
    """


class RepositoryNotFoundError(ApplicationError):
    def __init__(self, repo_name: str) -> None:
        super().__init__(f"Repository '{repo_name}' hasn't been ingested.")
        self.repo_name = repo_name


class RepositoryIncompatibleError(ApplicationError):
    """Ingested with an old/incompatible schema version - needs re-ingestion."""

    def __init__(
        self, repo_name: str, found_version: int, expected_version: int
    ) -> None:
        super().__init__(
            f"Repository '{repo_name}' was ingested with schema version {found_version}, "
            f"but this build expects version {expected_version} - re-ingest it."
        )
        self.repo_name = repo_name
        self.found_version = found_version
        self.expected_version = expected_version


class IngestionFailedError(ApplicationError):
    """Nothing usable could be ingested - bad path/URL, no in-scope files, no chunks produced."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"Could not ingest '{source}': {reason}")
        self.source = source
        self.reason = reason
