from langgraph.graph import END, StateGraph

from codebase_agent.graph.answer import generate_answer
from codebase_agent.graph.retrieve import retrieve
from codebase_agent.graph.router import route_question
from codebase_agent.graph.state import AgentState
from codebase_agent.llm import GroqClient
from codebase_agent.retrieval import CodeRetriever


def build_pipeline(
    llm: GroqClient | None = None, retriever: CodeRetriever | None = None
):
    llm = llm or GroqClient()
    retriever = retriever or CodeRetriever()

    graph = StateGraph(AgentState)
    graph.add_node("route_question", lambda state: route_question(llm, state))
    graph.add_node("retrieve", lambda state: retrieve(retriever, state))
    graph.add_node("generate_answer", lambda state: generate_answer(llm, state))

    graph.set_entry_point("route_question")
    graph.add_edge("route_question", "retrieve")
    graph.add_edge("retrieve", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


def answer_question(
    repo_name: str,
    question: str,
    llm: GroqClient | None = None,
    retriever: CodeRetriever | None = None,
) -> str:
    """Convenience entry point: run the pipeline once and return the final answer text."""
    pipeline = build_pipeline(llm, retriever)
    initial_state: AgentState = {
        "repo_name": repo_name,
        "question": question,
        "retrieval_strategy": "",
        "target_symbol": None,
        "retrieved_chunks": [],
        "answer": None,
    }
    final_state = pipeline.invoke(initial_state)
    return final_state["answer"] or ""
