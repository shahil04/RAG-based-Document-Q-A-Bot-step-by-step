from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.graph.state import RAGState

from app.graph.nodes import (
    retrieve_node,
    build_context_node,
    generate_answer_node,
)


def create_rag_graph():

    graph = StateGraph(RAGState)

    # Add nodes
    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "build_context",
        build_context_node
    )

    graph.add_node(
        "generate_answer",
        generate_answer_node
    )

    # Define workflow
    graph.add_edge(
        START,
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "build_context"
    )

    graph.add_edge(
        "build_context",
        "generate_answer"
    )

    graph.add_edge(
        "generate_answer",
        END
    )

    return graph.compile()