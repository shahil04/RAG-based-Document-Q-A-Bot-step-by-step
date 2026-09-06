from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.graph.state import RAGState

from app.graph.nodes import (
    load_history_node,
    rewrite_query_node,
    retrieve_node,
    build_context_node,
    check_relevance_node,
    retry_retrieval_node,
    generate_answer_node,
)


def relevance_router(state):

    is_relevant = state.get(
        "is_relevant",
        False
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    if is_relevant:

        return "generate_answer"

    if retry_count >= 1:

        return "generate_answer"

    return "retry_retrieval"



def validate_answer_node(state):

    answer = state.get(
        "answer",
        ""
    )

    context = state.get(
        "context",
        ""
    )

    question = state.get(
        "question",
        ""
    )

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=0
    )

    prompt = f"""
You are checking a RAG answer.

Determine whether the answer is supported
by the supplied document context.

Return ONLY:

YES

or

NO

Question:
{question}

Context:
{context}

Answer:
{answer}

Decision:
"""

    response = llm.invoke(prompt)

    return {
        "answer_valid": (
            response.content
            .strip()
            .upper()
            == "YES"
        )
    }

def create_rag_graph():

    graph = StateGraph(RAGState)

    # =========================
    # Nodes
    # =========================

    graph.add_node(
        "load_history",
        load_history_node
    )

    graph.add_node(
        "rewrite_query",
        rewrite_query_node
    )

    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "build_context",
        build_context_node
    )

    graph.add_node(
        "check_relevance",
        check_relevance_node
    )

    graph.add_node(
        "retry_retrieval",
        retry_retrieval_node
    )

    graph.add_node(
        "generate_answer",
        generate_answer_node
    )

    # =========================
    # Initial workflow
    # =========================

    graph.add_edge(
        START,
        "load_history"
    )

    graph.add_edge(
        "load_history",
        "rewrite_query"
    )

    graph.add_edge(
        "rewrite_query",
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "build_context"
    )

    graph.add_edge(
        "build_context",
        "check_relevance"
    )

    # =========================
    # Conditional routing
    # =========================

    graph.add_conditional_edges(
        "check_relevance",
        relevance_router,
        {
            "generate_answer":
                "generate_answer",

            "retry_retrieval":
                "retry_retrieval",
        }
    )

    # =========================
    # Retry
    # =========================

    graph.add_edge(
        "retry_retrieval",
        "rewrite_query"
    )

    # =========================
    # End
    # =========================

    graph.add_edge(
        "generate_answer",
        END
    )

    return graph.compile()