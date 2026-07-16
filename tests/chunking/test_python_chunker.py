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
