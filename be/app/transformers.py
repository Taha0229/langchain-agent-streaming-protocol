from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import GenerationChunk
from langgraph.stream import ProtocolEvent, StreamChannel, StreamTransformer

# from last_lab.enums import EngineGraphNodes
# from last_lab.common_models import QuizQuestion

from typing import TypedDict, List

class Question(TypedDict):
    id: int
    question: str
    options: List[str]
    answer: str
    difficulty: str
    explanation: str
    
class QuizQuestion(TypedDict):
    topic: str
    questions: List[Question]
    

class QuizTransformer(StreamTransformer):
    _native = True
    required_stream_modes = ("messages",) 

    def __init__(self, scope: tuple[str, ...] = ()) -> None:
        super().__init__(scope)

        self._scope_list: list[str] = list(scope)
        self.parser = JsonOutputParser()
        self.for_node = "quiz"

    def init(self):
        self.quiz_question: StreamChannel[QuizQuestion] = StreamChannel("quiz_question")

        self.acc_gen = None
        self.prev_parsed = None

        self.emitted = 0
        self.latest_questions = []

        return {
            "quiz_question": self.quiz_question,
        }

    def process(self, event: ProtocolEvent) -> bool:
        if event["method"] != "messages":
            return True

        params = event["params"]

        if params["namespace"] != self._scope_list:
            return True

        payload, metadata = params["data"]

        node: str | None = metadata.get("langgraph_node")

        if node != self.for_node:
            return True

        if payload.get("event") != "content-block-delta":
            return True

        delta = payload.get("delta") or {}

        if delta.get("type") != "text-delta":
            return True

        text = delta.get("text", "")

        chunk_gen = GenerationChunk(text=text)

        self.acc_gen = chunk_gen if self.acc_gen is None else self.acc_gen + chunk_gen

        parsed = self.parser.parse_result(
            [self.acc_gen],
            partial=True,
        )

        if parsed is None or parsed == self.prev_parsed:
            return True

        self.prev_parsed = parsed

        if not isinstance(parsed, list):
            return True

        self.latest_questions = parsed

        # Every question except the last one is considered complete.
        complete_upto = len(parsed) - 1

        while self.emitted < complete_upto:
            self.quiz_question.push(parsed[self.emitted])

            self.emitted += 1

        return True

    def finalize(self) -> None:
        if not isinstance(self.latest_questions, list):
            return

        if self.emitted < len(self.latest_questions):
            self.quiz_question.push(self.latest_questions[self.emitted])

            self.emitted += 1

    def fail(self, err: BaseException) -> None:
        self.quiz_question.fail(err)


from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import GenerationChunk
from langgraph.stream import ProtocolEvent, StreamChannel, StreamTransformer

# from last_lab.common_models import Flashcard
# from last_lab.enums import EngineGraphNodes


class Flashcard(TypedDict):
    id: int
    front: str
    back: str
    hint: str | None
    tags: List[str]


class FlashcardTransformer(StreamTransformer):
    _native = True
    required_stream_modes = ("messages",)

    def __init__(self, scope: tuple[str, ...] = ()) -> None:
        super().__init__(scope)

        self._scope_list: list[str] = list(scope)
        self.parser = JsonOutputParser()
        self.for_node = "flashcards"

    def init(self):
        self.flashcard: StreamChannel[Flashcard] = StreamChannel("flashcard")

        self.acc_gen = None
        self.prev_parsed = None

        self.emitted = 0
        self.latest_questions = []

        return {
            "flashcard": self.flashcard,
        }

    def process(self, event: ProtocolEvent) -> bool:
        if event["method"] != "messages":
            return True

        params = event["params"]

        if params["namespace"] != self._scope_list:
            return True

        payload, metadata = params["data"]

        node: str | None = metadata.get("langgraph_node")

        if node != self.for_node:
            return True

        if payload.get("event") != "content-block-delta":
            return True

        delta = payload.get("delta") or {}

        if delta.get("type") != "text-delta":
            return True

        text = delta.get("text", "")

        chunk_gen = GenerationChunk(text=text)

        self.acc_gen = chunk_gen if self.acc_gen is None else self.acc_gen + chunk_gen

        parsed = self.parser.parse_result(
            [self.acc_gen],
            partial=True,
        )

        if parsed is None or parsed == self.prev_parsed:
            return True

        self.prev_parsed = parsed

        if not isinstance(parsed, list):
            return True

        self.latest_questions = parsed

        # Every question except the last one is considered complete.
        complete_upto = len(parsed) - 1

        while self.emitted < complete_upto:
            self.flashcard.push(parsed[self.emitted])

            self.emitted += 1

        return True

    def finalize(self) -> None:
        if not isinstance(self.latest_questions, list):
            return

        if self.emitted < len(self.latest_questions):
            self.flashcard.push(self.latest_questions[self.emitted])

            self.emitted += 1

    def fail(self, err: BaseException) -> None:
        self.flashcard.fail(err)
