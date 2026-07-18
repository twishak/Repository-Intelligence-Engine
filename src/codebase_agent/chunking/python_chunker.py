import ast
import logging
from collections.abc import Iterable

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.ingestion.models import SourceFile

logger = logging.getLogger(__name__)

_FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def chunk_source_file(source: SourceFile) -> list[CodeChunk]:
    """Split a Python source file into function/method, class-skeleton, and module chunks."""
    try:
        tree = ast.parse(source.content, filename=source.path)
    except SyntaxError as e:
        logger.warning("Skipping %s - failed to parse: %s", source.path, e)
        return []

    chunks: list[CodeChunk] = []
    module_body_nodes: list[ast.stmt] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            chunks.append(
                _function_chunk(
                    source, node, qualified_name=node.name, chunk_type="function"
                )
            )
        elif isinstance(node, ast.ClassDef):
            chunks.extend(_process_class(source, node))
        else:
            module_body_nodes.append(node)

    module_chunk = _module_chunk(source, tree, module_body_nodes)
    if module_chunk is not None:
        chunks.append(module_chunk)

    return chunks


def chunk_source_files(sources: Iterable[SourceFile]) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for source in sources:
        chunks.extend(chunk_source_file(source))
    return chunks


def _process_class(
    source: SourceFile, node: ast.ClassDef, prefix: str = ""
) -> list[CodeChunk]:
    qualified_name = f"{prefix}{node.name}"
    chunks = [_class_skeleton_chunk(source, node, qualified_name)]
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            chunks.append(
                _function_chunk(
                    source,
                    item,
                    qualified_name=f"{qualified_name}.{item.name}",
                    chunk_type="method",
                )
            )
        elif isinstance(item, ast.ClassDef):
            chunks.extend(_process_class(source, item, prefix=f"{qualified_name}."))
    return chunks


def _function_chunk(
    source: SourceFile, node: _FunctionNode, qualified_name: str, chunk_type: str
) -> CodeChunk:
    start_line = _start_line(node)
    end_line = node.end_lineno
    body = _slice_lines(source.content, start_line, end_line)
    return CodeChunk(
        id=f"{source.path}::{chunk_type}::{qualified_name}",
        file_path=source.path,
        chunk_type=chunk_type,
        qualified_name=qualified_name,
        start_line=start_line,
        end_line=end_line,
        content=_with_header(source, qualified_name, body),
        docstring=ast.get_docstring(node),
    )


def _class_skeleton_chunk(
    source: SourceFile, node: ast.ClassDef, qualified_name: str
) -> CodeChunk:
    # TODO: a class with very many methods (e.g. a large test class) produces
    # one skeleton chunk containing every signature concatenated, with no
    # size cap - this can end up far larger than a typical chunk (743 real
    # chunks in requests/requests only ever produced one outlier, a 5000+
    # token test-class skeleton). embeddings.CodeEmbedder now buckets batches
    # by token length so this no longer forces unrelated short chunks to pad
    # to its length, but the chunk itself is still one large, less-precise
    # retrieval unit. Consider splitting oversized class skeletons into
    # multiple logical chunks (e.g. by method groups) - a retrieval-quality
    # improvement, separate from the embeddings-layer batching fix above.
    start_line = _start_line(node)
    end_line = node.end_lineno
    skeleton = _build_class_skeleton_text(node)
    return CodeChunk(
        id=f"{source.path}::class_skeleton::{qualified_name}",
        file_path=source.path,
        chunk_type="class_skeleton",
        qualified_name=qualified_name,
        start_line=start_line,
        end_line=end_line,
        content=_with_header(source, qualified_name, skeleton),
        docstring=ast.get_docstring(node),
    )


def _module_chunk(
    source: SourceFile, tree: ast.Module, residual_nodes: list[ast.stmt]
) -> CodeChunk | None:
    if not residual_nodes:
        return None

    # Each residual node is sliced individually and stitched together, so the
    # function/class bodies interspersed between them (chunked separately) are
    # excluded from the text - even though start/end_line below still span the
    # full range including those gaps, since that's the file's true extent.
    segments = [
        _slice_lines(source.content, _start_line(n), n.end_lineno)
        for n in residual_nodes
    ]
    body = "\n\n".join(segments)
    start_line = _start_line(residual_nodes[0])
    end_line = residual_nodes[-1].end_lineno

    return CodeChunk(
        id=f"{source.path}::module::<module>",
        file_path=source.path,
        chunk_type="module",
        qualified_name="<module>",
        start_line=start_line,
        end_line=end_line,
        content=_with_header(source, "<module>", body),
        docstring=ast.get_docstring(tree),
    )


def _build_class_skeleton_text(node: ast.ClassDef) -> str:
    bases = ", ".join(ast.unparse(base) for base in node.bases)
    header = f"class {node.name}({bases}):" if bases else f"class {node.name}:"

    parts = [header]
    docstring = ast.get_docstring(node)
    if docstring:
        parts.append(f'    """{docstring}"""')

    member_lines = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            signature = _signature_text(item)
            member_lines.append(
                "\n".join(f"    {line}" for line in signature.splitlines())
            )
        elif isinstance(item, ast.ClassDef):
            member_lines.append(f"    class {item.name}: ...")
    if not member_lines:
        member_lines.append("    ...")
    parts.append("\n\n".join(member_lines))

    return "\n".join(parts)


def _signature_text(node: _FunctionNode) -> str:
    # Temporarily swap the body for a stub so ast.unparse renders just the
    # signature (decorators, name, args, return type) - restored after, since
    # the same node is also used to build the full function chunk elsewhere.
    original_body = node.body
    node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
    try:
        return ast.unparse(node)
    finally:
        node.body = original_body


def _start_line(node: ast.AST) -> int:
    # FunctionDef/ClassDef.lineno points at the `def`/`class` keyword, not the
    # first decorator - so a chunk sliced from node.lineno would silently drop
    # decorators (e.g. @app.route(...)), which are often the answer to
    # "where is X handled" style questions.
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        return decorators[0].lineno
    return node.lineno


def _slice_lines(source_text: str, start_line: int, end_line: int) -> str:
    lines = source_text.splitlines()
    return "\n".join(lines[start_line - 1 : end_line])


def _with_header(source: SourceFile, qualified_name: str, body: str) -> str:
    return f"# file: {source.path}\n# {qualified_name}\n{body}"
