from codebase_agent.ingestion.models import SourceFile
from codebase_agent.intelligence.python_extractor import extract_repo_structure


def _source(path: str, content: str) -> SourceFile:
    return SourceFile(
        path=path,
        absolute_path=f"/repo/{path}",
        language="python",
        content=content,
        line_count=len(content.splitlines()),
    )


def test_extracts_function_and_class_symbols_with_module_qualified_names():
    source = _source(
        "pkg/service.py",
        '''
def start():
    """Start it."""


class Worker:
    """Does work."""

    def run(self):
        pass
''',
    )
    structure = extract_repo_structure([source])
    by_name = {s.qualified_name: s for s in structure.symbols}

    assert by_name["pkg.service.start"].kind == "function"
    assert by_name["pkg.service.start"].docstring == "Start it."
    assert by_name["pkg.service.Worker"].kind == "class"
    assert by_name["pkg.service.Worker.run"].kind == "method"


def test_same_named_top_level_symbols_in_different_files_do_not_collide():
    a = _source("scripts/one.py", "def main():\n    pass\n")
    b = _source("scripts/two.py", "def main():\n    pass\n")

    structure = extract_repo_structure([a, b])
    qualified_names = {s.qualified_name for s in structure.symbols}

    assert qualified_names == {"scripts.one.main", "scripts.two.main"}


def test_resolves_self_method_call():
    source = _source(
        "pkg/worker.py",
        "class Worker:\n"
        "    def run(self):\n"
        "        self.setup()\n"
        "\n"
        "    def setup(self):\n"
        "        pass\n",
    )
    structure = extract_repo_structure([source])
    call = next(c for c in structure.call_edges if c.callee_name == "self.setup")

    assert call.caller_qualified_name == "pkg.worker.Worker.run"
    assert call.callee_qualified_name == "pkg.worker.Worker.setup"


def test_resolves_bare_call_to_same_file_function_over_ambiguous_repo_wide_name():
    a = _source(
        "pkg/a.py",
        "def helper():\n    pass\n\n\ndef entry():\n    helper()\n",
    )
    b = _source("pkg/b.py", "def helper():\n    pass\n")

    structure = extract_repo_structure([a, b])
    call = next(
        c for c in structure.call_edges if c.caller_qualified_name == "pkg.a.entry"
    )

    assert call.callee_qualified_name == "pkg.a.helper"


def test_leaves_ambiguous_repo_wide_call_unresolved():
    a = _source("pkg/a.py", "def entry():\n    shared()\n")
    b = _source("pkg/b.py", "def shared():\n    pass\n")
    c = _source("pkg/c.py", "def shared():\n    pass\n")

    structure = extract_repo_structure([a, b, c])
    call = next(c for c in structure.call_edges if c.callee_name == "shared")

    assert call.callee_qualified_name is None


def test_unresolved_external_call_kept_with_none_qualified_name():
    source = _source("pkg/a.py", "import os\n\n\ndef entry():\n    os.getcwd()\n")
    structure = extract_repo_structure([source])
    call = next(c for c in structure.call_edges if c.callee_name == "os.getcwd")

    assert call.callee_qualified_name is None


def test_resolves_inheritance_within_same_repo():
    source = _source(
        "pkg/models.py", "class Base:\n    pass\n\n\nclass Child(Base):\n    pass\n"
    )
    structure = extract_repo_structure([source])
    edge = next(
        e
        for e in structure.inherits_edges
        if e.class_qualified_name == "pkg.models.Child"
    )

    assert edge.base_qualified_name == "pkg.models.Base"


def test_unresolved_external_base_class():
    source = _source(
        "pkg/models.py", "import abc\n\n\nclass Thing(abc.ABC):\n    pass\n"
    )
    structure = extract_repo_structure([source])
    edge = next(
        e
        for e in structure.inherits_edges
        if e.class_qualified_name == "pkg.models.Thing"
    )

    assert edge.base_qualified_name is None
    assert edge.base_name == "abc.ABC"


def test_resolves_absolute_import_to_repo_file():
    a = _source("pkg/a.py", "import pkg.b\n")
    b = _source("pkg/b.py", "x = 1\n")
    structure = extract_repo_structure([a, b])
    edge = next(e for e in structure.import_edges if e.imported_module == "pkg.b")

    assert edge.resolved_file == "pkg/b.py"


def test_resolves_relative_import_to_repo_file():
    a = _source("pkg/sub/a.py", "from .. import shared\n")
    shared = _source("pkg/shared.py", "x = 1\n")
    structure = extract_repo_structure([a, shared])
    edge = next(e for e in structure.import_edges if e.importer_file == "pkg/sub/a.py")

    assert edge.resolved_file == "pkg/shared.py"


def test_unresolved_external_import_kept_with_none_resolved_file():
    source = _source("pkg/a.py", "import numpy\n")
    structure = extract_repo_structure([source])
    edge = structure.import_edges[0]

    assert edge.imported_module == "numpy"
    assert edge.resolved_file is None


def test_resolves_import_in_a_src_layout_repo():
    # src/ is a source root, not part of the import namespace (PyPA's "src
    # layout" convention) - `import pkg.b` must resolve even though the
    # files live at src/pkg/a.py and src/pkg/b.py, not pkg/a.py.
    a = _source("src/pkg/a.py", "import pkg.b\n")
    b = _source("src/pkg/b.py", "x = 1\n")

    structure = extract_repo_structure([a, b])

    edge = next(e for e in structure.import_edges if e.imported_module == "pkg.b")
    assert edge.resolved_file == "src/pkg/b.py"


def test_symbol_qualified_names_omit_the_src_prefix():
    source = _source("src/pkg/a.py", "def foo():\n    pass\n")

    structure = extract_repo_structure([source])

    assert {s.qualified_name for s in structure.symbols} == {"pkg.a.foo"}


def test_skips_file_with_syntax_error_without_crashing():
    bad = _source("pkg/broken.py", "def bad(:\n    pass\n")
    good = _source("pkg/ok.py", "def ok():\n    pass\n")

    structure = extract_repo_structure([bad, good])

    assert {s.qualified_name for s in structure.symbols} == {"pkg.ok.ok"}
