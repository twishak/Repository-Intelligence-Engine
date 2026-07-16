from codebase_agent.graph.state import AgentState
from codebase_agent.llm import GroqClient
from codebase_agent.storage.models import RetrievedChunk

_SYSTEM_PROMPT = (
    "You are a codebase-understanding assistant. Answer the user's question using "
    "ONLY the provided code context - never guess at code you haven't been shown. "
    "Cite every claim with the source location in the form `path/to/file.py:start-end`. "
    "If the context is insufficient to answer, say so explicitly instead of guessing."
)


def generate_answer(llm: GroqClient, state: AgentState) -> dict:
    context = _format_chunks(state["retrieved_chunks"])
    user_content = f"Question: {state['question']}\n\nRetrieved context:\n{context}"

    message = llm.chat(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
    )
    return {"answer": message.content}


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no matching code found)"
    return "\n\n---\n\n".join(
        f"# {c.qualified_name} ({c.file_path}:{c.start_line}-{c.end_line})\n{c.content}"
        for c in chunks
    )
