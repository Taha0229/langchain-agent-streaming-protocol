r"""A LangGraph study assistant.

    START -> notes -> quiz ------\
                   \-> flashcards -> deep_dive -> END

Notes are written first. Quiz and flashcards then fan out and run in parallel
off those notes, since neither depends on the other. The deep dive joins them
and produces the long streaming answer.
"""

from typing import Any, Iterator, TypedDict, Sequence, Callable

from langchain_openai import ChatOpenAI

from app.chains import (
    create_deep_dive_chain,
    create_flashcard_chain,
    create_note_chain,
    create_quiz_chain,
)
from langgraph.graph import END, START, StateGraph

DEFAULT_MODEL = "gpt-4o-mini"


class StudyState(TypedDict, total=False):
    """Shared state. Each node reads what it needs and writes its own key."""

    topic: str
    num_questions: int
    num_cards: int
    notes: str
    quiz: list[dict[str, Any]]
    flashcards: list[dict[str, Any]]
    deep_dive: str


def get_model(model_name: str = DEFAULT_MODEL, temperature: float = 0.3) -> ChatOpenAI:
    """Build the chat model every chain shares."""
    return ChatOpenAI(model=model_name, temperature=temperature)


def build_study_graph(
    checkpointer,
    model: ChatOpenAI | None = None,
    transformers: Sequence[Callable[[tuple[str, ...]], Any]] | None = None,
):
    """Wire the four chains into a compiled graph."""
    model = model or get_model()

    # Built once at graph-construction time, not per invocation.
    note_chain = create_note_chain(model)
    quiz_chain = create_quiz_chain(model)
    flashcard_chain = create_flashcard_chain(model)
    deep_dive_chain = create_deep_dive_chain(model)

    def notes_node(state: StudyState) -> StudyState:
        notes = note_chain.invoke({"topic": state["topic"]})
        return {"notes": notes}

    def quiz_node(state: StudyState) -> StudyState:
        quiz = quiz_chain.invoke(
            {
                "topic": state["topic"],
                "num_questions": state.get("num_questions", 5),
            }
        )
        return {"quiz": quiz}

    def flashcards_node(state: StudyState) -> StudyState:
        cards = flashcard_chain.invoke(
            {
                "topic": state["topic"],
                "num_cards": state.get("num_cards", 8),
            }
        )
        return {"flashcards": cards}

    def deep_dive_node(state: StudyState) -> StudyState:
        essay = deep_dive_chain.invoke(
            {"topic": state["topic"], "notes": state["notes"]}
        )
        return {"deep_dive": essay}

    builder = StateGraph(StudyState)
    builder.add_node("notes", notes_node)
    builder.add_node("quiz", quiz_node)
    builder.add_node("flashcards", flashcards_node)
    builder.add_node("deep_dive", deep_dive_node)

    builder.add_edge(START, "notes")
    # Fan out: both run off the same notes, in parallel.
    builder.add_edge(START, "quiz")
    builder.add_edge(START, "flashcards")
    # Fan in: deep_dive waits for both to land.
    builder.add_edge("quiz", "deep_dive")
    builder.add_edge("flashcards", "deep_dive")
    builder.add_edge("deep_dive", END)

    return builder.compile(checkpointer=checkpointer, transformers=transformers)


# def stream_tokens(graph, topic: str, node: str = "deep_dive", **kwargs) -> Iterator[str]:
#     """Yield tokens as one node's chain produces them.

#     "messages" stream mode surfaces per-token chunks from any chat model called
#     inside the graph, tagged with the node that produced them, so filtering on
#     langgraph_node isolates a single node's output.
#     """
#     payload: dict[str, Any] = {"topic": topic, **kwargs}
#     for chunk, metadata in graph.stream(payload, stream_mode="messages"):
#         if metadata.get("langgraph_node") != node:
#             continue
#         # .text is a property in langchain-core 1.x and was a method before it.
#         text = getattr(chunk, "text", None)
#         if callable(text):
#             text = text()
#         if text:
#             yield text
