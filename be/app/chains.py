"""Chain factories for the study-assistant graph.

Each factory takes an already-constructed chat model and pipes it into a
prompt that is defined at module level, so the prompts stay inspectable and
editable without touching the wiring.
"""

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Prompts
#
# Literal braces in a ChatPromptTemplate must be doubled, so every JSON schema
# below is written with {{ }} and renders as single braces at format time.
# ---------------------------------------------------------------------------

NOTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a study assistant who writes clear, well-structured revision "
            "notes. Use short paragraphs and markdown headings. Explain jargon the "
            "first time it appears. Do not pad the answer with filler.",
        ),
        (
            "human",
            "Write revision notes on the following topic.\n\nTopic: {topic}",
        ),
    ]
)

QUIZ_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You write multiple-choice quizzes from study notes.\n\n"
            "Respond with JSON only. No markdown fence, no commentary. "
            "Return a JSON array of exactly {num_questions} quiz question objects. "
            "Do not wrap the array in an object — the top-level value is the list "
            "itself.\n"
            "Every element must match this schema exactly:\n"
            "[\n"
            "  {{\n"
            '    "id": integer, starting at 1 and increasing by 1,\n'
            '    "question": string,\n'
            '    "options": array of exactly 4 distinct strings,\n'
            '    "answer": string, must match one element of options verbatim,\n'
            '    "difficulty": one of "easy", "medium", "hard",\n'
            '    "explanation": string, one or two sentences on why the answer is correct\n'
            "  }}\n"
            "]",
        ),
        (
            "human",
            "Write {num_questions} quiz questions on '{topic}' using only the notes below.\n\n"
        ),
    ]
)

FLASHCARD_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You turn study notes into flashcards for spaced repetition.\n\n"
            "Respond with JSON only. No markdown fence, no commentary. "
            "Return a JSON array of exactly {num_cards} flashcard objects. "
            "Do not wrap the array in an object — the top-level value is the list "
            "itself.\n"
            "Every element must match this schema exactly:\n"
            "[\n"
            "  {{\n"
            '    "id": integer, starting at 1 and increasing by 1,\n'
            '    "front": string, a single question or prompt,\n'
            '    "back": string, the answer, at most two sentences,\n'
            '    "hint": string or null,\n'
            '    "tags": array of 1 to 3 lowercase strings\n'
            "  }}\n"
            "]\n\n"
            "Keep each card to one idea. Never put two facts on one card.",
        ),
        (
            "human",
            "Write {num_cards} flashcards on '{topic}' using only the notes below.\n\n"
        ),
    ]
)

DEEP_DIVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You write long-form explanatory essays for a curious reader who knows "
            "the basics but wants depth.\n\n"
            "Structure the answer as:\n"
            "1. Why this topic matters\n"
            "2. The core mechanism, explained from first principles\n"
            "3. A worked example\n"
            "4. Common misconceptions\n"
            "5. Where to go next\n\n"
            "Write flowing prose under markdown headings. Aim for roughly 800 words. "
            "Return plain text, never JSON.",
        ),
        (
            "human",
            "Write a deep dive on '{topic}'.\n\n"
        ),
    ]
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def create_note_chain(model):
    """Topic -> revision notes as a plain string."""
    return NOTE_PROMPT | model | StrOutputParser()


def create_quiz_chain(model):
    """Topic plus notes -> list of quiz questions matching the schema in QUIZ_PROMPT."""
    return QUIZ_PROMPT | model | JsonOutputParser()


def create_flashcard_chain(model):
    """Topic plus notes -> list of flashcards matching the schema in FLASHCARD_PROMPT."""
    return FLASHCARD_PROMPT | model | JsonOutputParser()


def create_deep_dive_chain(model):
    """Topic plus notes -> a long string, built to be streamed token by token."""
    return DEEP_DIVE_PROMPT | model | StrOutputParser()
