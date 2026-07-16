import ast
import logging
from collections.abc import Iterable
from dataclasses import dataclass

from codebase_agent.ingestion.models import SourceFile
from codebase_agent.intelligence.models import (
    CallEdge,
    ImportEdge,
    InheritsEdge,
    RepoStructure,
    Symbol,
)

logger = logging.getLogger(__name__)

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def extract_repo_structure(sources: Iterable[SourceFile]) -> RepoStructure:
    """Statically extract symbols, imports, calls, and class hierarchy from a
    repo's Python sources.

    Call and inheritance resolution is best-effort: Python's dynamism (duck
    typing, `getattr`, monkeypatching, metaclasses) means a fully sound static
    call graph isn't possible. Edges that can't be matched to a known repo
    symbol are still recorded, just with `*_qualified_name=None`, so callers
    can distinguish "resolved to repo code" from "external or dynamic".
    """
    sources = list(sources)
    module_map = _build_module_map(sources)

    symbols: list[Symbol] = []
    pending_calls: list[_PendingCall] = []
    pending_bases: list[_PendingBase] = []
    import_edges: list[ImportEdge] = []

    for source in sources:
        try:
            tree = ast.parse(source.content, filename=source.path)
        except SyntaxError as e:
            logger.warning("Skipping %s - failed to parse: %s", source.path, e)
            continue

        file_symbols, file_calls, file_bases = _extract_file(source, tree)
        symbols.extend(file_symbols)
        pending_calls.extend(file_calls)
        pending_bases.extend(file_bases)
        import_edges.extend(_extract_imports(source, tree, module_map))

    by_qualified_name = {s.qualified_name: s for s in symbols}
    by_short_name = _index_by_short_name(symbols)

    call_edges = [
        _resolve_call(c, by_qualified_name, by_short_name) for c in pending_calls
    ]
    inherits_edges = [
        _resolve_base(b, by_qualified_name, by_short_name) for b in pending_bases
    ]

    return RepoStructure(
        symbols=symbols,
        import_edges=import_edges,
        call_edges=call_edges,
        inherits_edges=inherits_edges,
    )


@dataclass(frozen=True)
class _PendingCall:
    caller_qualified_name: str
    callee_name: str
    enclosing_class: str | None
    file_path: str
    line: int


@dataclass(frozen=True)
class _PendingBase:
    class_qualified_name: str
    base_name: str
    file_path: str


def _extract_file(
    source: SourceFile, tree: ast.Module
) -> tuple[list[Symbol], list[_PendingCall], list[_PendingBase]]:
    # Qualified names are prefixed with the file's dotted module path so
    # same-named top-level symbols in different files (e.g. every script
    # having its own `main`) don't collide in the repo-wide symbol table.
    module_prefix = _module_name_for_path(source.path)
    prefix = f"{module_prefix}." if module_prefix else ""

    symbols: list[Symbol] = []
    calls: list[_PendingCall] = []
    bases: list[_PendingBase] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            qname = f"{prefix}{node.name}"
            symbols.append(_function_symbol(source, node, qname, "function"))
            calls.extend(_extract_calls(source, node, qname, enclosing_class=None))
        elif isinstance(node, ast.ClassDef):
            c_symbols, c_calls, c_bases = _process_class(source, node, prefix=prefix)
            symbols.extend(c_symbols)
            calls.extend(c_calls)
            bases.extend(c_bases)

    return symbols, calls, bases


def _process_class(
    source: SourceFile, node: ast.ClassDef, prefix: str = ""
) -> tuple[list[Symbol], list[_PendingCall], list[_PendingBase]]:
    qualified_name = f"{prefix}{node.name}"
    symbols = [_class_symbol(source, node, qualified_name)]
    calls: list[_PendingCall] = []
    bases = [
        _PendingBase(qualified_name, name, source.path)
        for name in (_dotted(b) for b in node.bases)
        if name
    ]

    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            method_qname = f"{qualified_name}.{item.name}"
            symbols.append(_function_symbol(source, item, method_qname, "method"))
            calls.extend(
                _extract_calls(
                    source, item, method_qname, enclosing_class=qualified_name
                )
            )
        elif isinstance(item, ast.ClassDef):
            n_symbols, n_calls, n_bases = _process_class(
                source, item, prefix=f"{qualified_name}."
            )
            symbols.extend(n_symbols)
            calls.extend(n_calls)
            bases.extend(n_bases)

    return symbols, calls, bases


def _extract_calls(
    source: SourceFile,
    func_node: _FunctionNode,
    caller_qname: str,
    enclosing_class: str | None,
) -> list[_PendingCall]:
    # Walk each body statement individually (not decorator_list or args
    # defaults) so decorator applications like @app.route(...) aren't
    # misattributed as calls made from inside the function body.
    calls = []
    for stmt in func_node.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Call):
                name = _dotted(n.func)
                if name is not None:
                    calls.append(
                        _PendingCall(
                            caller_qname, name, enclosing_class, source.path, n.lineno
                        )
                    )
    return calls


def _resolve_call(
    call: _PendingCall, by_qname: dict[str, Symbol], by_short: dict[str, list[Symbol]]
) -> CallEdge:
    resolved = _resolve_reference(
        call.callee_name, call.enclosing_class, call.file_path, by_qname, by_short
    )
    return CallEdge(
        caller_qualified_name=call.caller_qualified_name,
        callee_name=call.callee_name,
        callee_qualified_name=resolved,
        file_path=call.file_path,
        line=call.line,
    )


def _resolve_base(
    base: _PendingBase, by_qname: dict[str, Symbol], by_short: dict[str, list[Symbol]]
) -> InheritsEdge:
    resolved = _resolve_reference(
        base.base_name, None, base.file_path, by_qname, by_short
    )
    return InheritsEdge(
        class_qualified_name=base.class_qualified_name,
        base_name=base.base_name,
        base_qualified_name=resolved,
    )


def _resolve_reference(
    raw_name: str,
    enclosing_class: str | None,
    file_path: str,
    by_qname: dict[str, Symbol],
    by_short: dict[str, list[Symbol]],
) -> str | None:
    """Best-effort match of a raw call/base expression to a known symbol.

    Tries, in order: self./cls. attribute on the enclosing class, an exact
    qualified-name match, an unambiguous same-file short-name match (the
    common case - a bare call to a function defined earlier in the same
    file), then an unambiguous repo-wide short-name match. Ambiguous short
    names (multiple files/classes defining the same name) are deliberately
    left unresolved rather than guessed at.
    """
    if enclosing_class and (
        raw_name.startswith("self.") or raw_name.startswith("cls.")
    ):
        _, _, rest = raw_name.partition(".")
        if "." not in rest:
            candidate = f"{enclosing_class}.{rest}"
            if candidate in by_qname:
                return candidate

    if raw_name in by_qname:
        return raw_name

    last_segment = raw_name.rsplit(".", 1)[-1]
    candidates = by_short.get(last_segment, [])

    same_file = [s for s in candidates if s.file_path == file_path]
    if len(same_file) == 1:
        return same_file[0].qualified_name

    if len(candidates) == 1:
        return candidates[0].qualified_name

    return None


def _extract_imports(
    source: SourceFile, tree: ast.Module, module_map: dict[str, str]
) -> list[ImportEdge]:
    base_package = _package_of(source.path)
    edges: list[ImportEdge] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    ImportEdge(source.path, alias.name, module_map.get(alias.name))
                )
        elif isinstance(node, ast.ImportFrom):
            base_module = _absolute_module_name(base_package, node.module, node.level)
            if any(alias.name == "*" for alias in node.names):
                edges.append(
                    ImportEdge(source.path, base_module, module_map.get(base_module))
                )
                continue
            for alias in node.names:
                # `alias.name` might itself be a submodule (from pkg import
                # submodule) or a symbol defined inside base_module (from pkg
                # import some_func) - try the former first, fall back to the
                # latter, since either way the file depends on base_module.
                candidate = f"{base_module}.{alias.name}" if base_module else alias.name
                if candidate in module_map:
                    edges.append(
                        ImportEdge(source.path, candidate, module_map[candidate])
                    )
                else:
                    edges.append(
                        ImportEdge(
                            source.path, base_module, module_map.get(base_module)
                        )
                    )

    return edges


def _build_module_map(sources: list[SourceFile]) -> dict[str, str]:
    return {_module_name_for_path(s.path): s.path for s in sources}


def _module_name_for_path(path: str) -> str:
    stem = path[:-3] if path.endswith(".py") else path
    parts = stem.split("/")
    # "src layout" (PyPA's recommended convention: packages live under a
    # src/ directory that isn't itself part of the import namespace, e.g.
    # this project's own pyproject.toml `where = ["src"]`) - without this,
    # every import in a src-layout repo fails to resolve, since real import
    # statements never say `import src.pkg.module`.
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_of(path: str) -> str:
    module_name = _module_name_for_path(path)
    if path.endswith("/__init__.py") or path == "__init__.py":
        return module_name
    return module_name.rsplit(".", 1)[0] if "." in module_name else ""


def _absolute_module_name(base_package: str, module: str | None, level: int) -> str:
    if level == 0:
        return module or ""

    base_parts = base_package.split(".") if base_package else []
    up = level - 1
    target_parts = base_parts[: len(base_parts) - up] if up else base_parts
    target_package = ".".join(p for p in target_parts if p)

    if module:
        return f"{target_package}.{module}" if target_package else module
    return target_package


def _index_by_short_name(symbols: list[Symbol]) -> dict[str, list[Symbol]]:
    index: dict[str, list[Symbol]] = {}
    for symbol in symbols:
        short_name = symbol.qualified_name.rsplit(".", 1)[-1]
        index.setdefault(short_name, []).append(symbol)
    return index


def _function_symbol(
    source: SourceFile, node: _FunctionNode, qualified_name: str, kind: str
) -> Symbol:
    return Symbol(
        qualified_name=qualified_name,
        kind=kind,
        file_path=source.path,
        start_line=_start_line(node),
        end_line=node.end_lineno,
        signature=_signature_text(node),
        docstring=ast.get_docstring(node),
        decorators=tuple(ast.unparse(d) for d in node.decorator_list),
    )


def _class_symbol(
    source: SourceFile, node: ast.ClassDef, qualified_name: str
) -> Symbol:
    short_name = qualified_name.rsplit(".", 1)[-1]
    bases = ", ".join(ast.unparse(b) for b in node.bases)
    signature = f"class {short_name}({bases}):" if bases else f"class {short_name}:"
    return Symbol(
        qualified_name=qualified_name,
        kind="class",
        file_path=source.path,
        start_line=_start_line(node),
        end_line=node.end_lineno,
        signature=signature,
        docstring=ast.get_docstring(node),
        decorators=tuple(ast.unparse(d) for d in node.decorator_list),
    )


def _signature_text(node: _FunctionNode) -> str:
    # Swap the body for a stub so ast.unparse renders just the signature
    # (decorators, name, args, return type), then restore it - the same node
    # object is reused, we're not mutating a copy.
    original_body = node.body
    node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
    try:
        return ast.unparse(node)
    finally:
        node.body = original_body


def _start_line(node: ast.AST) -> int:
    # FunctionDef/ClassDef.lineno points at the def/class keyword, not the
    # first decorator - use the decorator's line when present so a symbol's
    # range includes it.
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        return decorators[0].lineno
    return node.lineno


def _dotted(expr: ast.expr) -> str | None:
    try:
        return ast.unparse(expr)
    except Exception:
        return None
