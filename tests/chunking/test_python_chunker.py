from codebase_agent.chunking.python_chunker import chunk_source_file
from codebase_agent.ingestion.models import SourceFile


def _source(content: str, path: str = "sample.py") -> SourceFile:
    return SourceFile(
        path=path,
        absolute_path=f"/repo/{path}",
        language="python",
        content=content,
        line_count=len(content.splitlines()),
    )


def test_top_level_function_chunk_includes_decorator():
    content = (
        "import os\n\n"
        "@app.route('/users')\n"
        "def list_users():\n"
        '    """List all users."""\n'
        "    return os.listdir('.')\n"
    )
    chunks = chunk_source_file(_source(content))

    func_chunks = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunks) == 1
    chunk = func_chunks[0]
    assert chunk.qualified_name == "list_users"
    assert "@app.route" in chunk.content
    assert "def list_users" in chunk.content
    assert chunk.docstring == "List all users."


def test_class_produces_skeleton_and_method_chunks():
    content = (
        "class PaymentHandler:\n"
        '    """Handles payments."""\n\n'
        "    def handle_refund(self, request):\n"
        "        return process(request)\n\n"
        "    def validate(self, data):\n"
        "        return bool(data)\n"
    )
    chunks = chunk_source_file(_source(content))

    skeletons = [c for c in chunks if c.chunk_type == "class_skeleton"]
    methods = [c for c in chunks if c.chunk_type == "method"]

    assert [s.qualified_name for s in skeletons] == ["PaymentHandler"]
    assert "def handle_refund" in skeletons[0].content
    assert "def validate" in skeletons[0].content
    assert "process(request)" not in skeletons[0].content  # bodies stripped

    assert {m.qualified_name for m in methods} == {
        "PaymentHandler.handle_refund",
        "PaymentHandler.validate",
    }


def test_nested_class_gets_dotted_qualified_name():
    content = (
        "class Outer:\n    class Config:\n        arbitrary_types_allowed = True\n"
    )
    chunks = chunk_source_file(_source(content))

    skeletons = {c.qualified_name for c in chunks if c.chunk_type == "class_skeleton"}
    assert skeletons == {"Outer", "Outer.Config"}


def test_module_level_residual_excludes_function_and_class_bodies():
    content = (
        "import os\n\n"
        "TIMEOUT = 30\n\n"
        "def helper():\n"
        "    return os.getcwd()\n\n"
        "class Thing:\n"
        "    pass\n"
    )
    chunks = chunk_source_file(_source(content))

    module_chunks = [c for c in chunks if c.chunk_type == "module"]
    assert len(module_chunks) == 1
    module_content = module_chunks[0].content
    assert "import os" in module_content
    assert "TIMEOUT = 30" in module_content
    assert "def helper" not in module_content
    assert "class Thing" not in module_content


def test_syntax_error_returns_no_chunks():
    chunks = chunk_source_file(_source("def broken(:\n"))
    assert chunks == []


def test_function_chunk_id_includes_line_span():
    content = "def foo():\n    return 1\n"
    chunks = chunk_source_file(_source(content, path="a.py"))

    chunk = next(c for c in chunks if c.chunk_type == "function")
    assert chunk.id == f"a.py::function::foo::{chunk.start_line}-{chunk.end_line}"


def test_module_level_overloads_get_unique_chunk_ids_and_all_ingest():
    # Regression test: @overload stubs plus the real implementation used to
    # collide on id (path::function::name), which crashed ingestion with a
    # DuplicateIDError on insert into Chroma. All three defs must now be kept,
    # each with a distinct id.
    content = (
        "from typing import overload\n\n"
        "@overload\n"
        "def parse(value: str) -> str: ...\n\n"
        "@overload\n"
        "def parse(value: int) -> int: ...\n\n"
        "def parse(value):\n"
        "    return value\n"
    )
    chunks = chunk_source_file(_source(content))

    func_chunks = [c for c in chunks if c.chunk_type == "function"]
    assert len(func_chunks) == 3
    assert len({c.id for c in func_chunks}) == 3
    assert all(c.qualified_name == "parse" for c in func_chunks)


def test_class_method_overloads_get_unique_chunk_ids_and_all_ingest():
    content = (
        "from typing import overload\n\n"
        "class Parser:\n"
        "    @overload\n"
        "    def parse(self, value: str) -> str: ...\n\n"
        "    @overload\n"
        "    def parse(self, value: int) -> int: ...\n\n"
        "    def parse(self, value):\n"
        "        return value\n"
    )
    chunks = chunk_source_file(_source(content))

    method_chunks = [c for c in chunks if c.chunk_type == "method"]
    assert len(method_chunks) == 3
    assert len({c.id for c in method_chunks}) == 3
    assert all(c.qualified_name == "Parser.parse" for c in method_chunks)


def test_all_chunk_ids_in_a_file_are_unique():
    # The property that actually matters for Chroma insertion: no two chunks
    # anywhere in a file's output - functions, methods, class skeletons,
    # module - collide on id, even with overloads mixed in.
    content = (
        "from typing import overload\n\n"
        "@overload\n"
        "def parse(value: str) -> str: ...\n"
        "def parse(value):\n"
        "    return value\n\n"
        "class Parser:\n"
        "    @overload\n"
        "    def parse(self, value: str) -> str: ...\n"
        "    def parse(self, value):\n"
        "        return value\n"
    )
    chunks = chunk_source_file(_source(content))

    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
