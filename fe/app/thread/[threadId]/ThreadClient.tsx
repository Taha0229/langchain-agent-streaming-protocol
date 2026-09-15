"use client";

import {
  HttpAgentServerAdapter,
  StreamProvider,
  useChannel,
  useStreamContext,
  type AnyStream,
  type Event,
} from "@langchain/react";
import {
  createContext,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Flashcard = {
  id: number;
  front: string;
  back: string;
  hint: string | null;
  tags: string[];
};

type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  answer: string;
  difficulty: string;
  explanation: string;
};

// One run produces ~2350 message events. The default 4096 buffer would start
// dropping the oldest of them partway through a second run, which could take
// the current run's opening `running` marker with it.
const MESSAGE_BUFFER = 16384;

export default function ThreadClient({ threadId }: { threadId: string }) {
  const transport = useMemo(
    () =>
      new HttpAgentServerAdapter({
        apiUrl: "http://localhost:8000",
        threadId,
        paths: {
          commands: `/threads/${threadId}/commands`,
          stream: `/threads/${threadId}/stream`,
        },
      }),
    [threadId],
  );

  // Profiling switch. A thread id prefixed `stable-` freezes the stream handle
  // so the panels stop waking on unrelated root-snapshot churn. See
  // development_notes/frontend-notes.md for why this is off by default.
  const stable = threadId.startsWith("stable-");

  return (
    <StreamProvider transport={transport} threadId={threadId}>
      <div className="flex w-full max-w-6xl flex-col gap-4 p-6">
        <p className="text-xs text-zinc-500">{threadId}</p>
        <StreamBoundary stable={stable}>
          <TopicForm />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <NotesPanel />
            <DeepDivePanel />
            <FlashcardsPanel />
            <QuizPanel />
          </div>
        </StreamBoundary>
      </div>
    </StreamProvider>
  );
}

const StreamBox = createContext<AnyStream | null>(null);

/**
 * Consumes the stream context once on behalf of the whole subtree.
 *
 * With `stable`, the handle is pinned in a ref so its identity never changes and
 * the panels below wake only for their own channels. Without it, the live
 * context value passes straight through and every panel re-renders on every
 * root-snapshot flush. Only the selector hooks may read the pinned handle:
 * `isLoading` and friends would be frozen at first render.
 */
function StreamBoundary({
  stable,
  children,
}: {
  stable: boolean;
  children: ReactNode;
}) {
  const stream = useStreamContext();
  const pinned = useRef(stream);

  return (
    <StreamBox.Provider value={stable ? pinned.current : stream}>
      {children}
    </StreamBox.Provider>
  );
}

function useStreamHandle(): AnyStream {
  const stream = useContext(StreamBox);
  if (stream == null) throw new Error("Panel rendered outside StreamBoundary");
  return stream;
}

/** Each run opens with a root lifecycle `running` event. */
function isRunStart(event: Event) {
  return event.method === "lifecycle" && event.params.data.event === "running";
}

/**
 * Collect every payload published on one `custom:<name>` channel for the
 * current run. `useExtension` would keep only the newest, and the channel log
 * accumulates across runs, so the reducer restarts at each run boundary. Keys
 * come off the event seq, which is unique thread-wide.
 */
function useRunPayloads<T>(channel: `custom:${string}`) {
  const events = useChannel(useStreamHandle(), [channel, "lifecycle"]);

  return useMemo(() => {
    let items: { key: string; value: T }[] = [];
    events.forEach((event, index) => {
      if (isRunStart(event)) items = [];
      else if (event.method === "custom") {
        items.push({
          key: String(event.seq ?? index),
          value: event.params.data.payload as T,
        });
      }
    });
    return items;
  }, [events]);
}

/**
 * Reassemble one node's streamed text from raw message deltas. This is the
 * client-side counterpart to what the Python transformers do server-side: walk
 * `content-block-delta` frames and append their text as it arrives.
 */
function useNodeText(node: string) {
  const events = useChannel(
    useStreamHandle(),
    ["messages", "lifecycle"],
    undefined,
    { bufferSize: MESSAGE_BUFFER },
  );

  return useMemo(() => {
    let text = "";
    for (const event of events) {
      if (isRunStart(event)) {
        text = "";
        continue;
      }
      if (event.method !== "messages") continue;
      if (event.params.node !== node) continue;

      const data = event.params.data;
      if (data.event !== "content-block-delta") continue;
      if (data.delta.type !== "text-delta") continue;

      text += data.delta.text;
    }
    return text;
  }, [events, node]);
}

function TopicForm() {
  const stream = useStreamContext();
  const [topic, setTopic] = useState("Photosynthesis");

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        stream.submit({ topic, num_questions: 5, num_cards: 5 });
      }}
      className="flex gap-2"
    >
      <input
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
        className="flex-1 rounded-md border border-zinc-300 px-3 py-2"
      />
      <button
        type="submit"
        disabled={stream.isLoading}
        className="rounded-md bg-black px-6 py-2 text-white disabled:opacity-50"
      >
        {stream.isLoading ? "Running…" : "Run"}
      </button>
    </form>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex min-h-64 flex-col rounded-lg border border-zinc-200 bg-white">
      <h2 className="border-b border-zinc-200 px-4 py-2 text-sm font-semibold text-zinc-700">
        {title}
      </h2>
      <div className="max-h-96 flex-1 overflow-auto p-4">{children}</div>
    </section>
  );
}

function Empty({ label }: { label: string }) {
  return <p className="text-sm text-zinc-400">{label}</p>;
}

function Prose({ text }: { text: string }) {
  return (
    <div className="text-sm leading-relaxed text-zinc-800 [&_code]:rounded [&_code]:bg-zinc-100 [&_code]:px-1 [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mt-2 [&_h3]:font-semibold [&_li]:mb-1 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-2 [&_strong]:font-semibold [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5">
      <Markdown remarkPlugins={[remarkGfm]}>{text}</Markdown>
    </div>
  );
}

function NotesPanel() {
  const text = useNodeText("notes");

  return (
    <Panel title="Notes">
      {text ? <Prose text={text} /> : <Empty label="Waiting for notes…" />}
    </Panel>
  );
}

function DeepDivePanel() {
  const text = useNodeText("deep_dive");

  return (
    <Panel title="Deep dive">
      {text ? <Prose text={text} /> : <Empty label="Waiting for deep dive…" />}
    </Panel>
  );
}

function FlashcardsPanel() {
  const cards = useRunPayloads<Flashcard>("custom:flashcard");

  return (
    <Panel title={`Flashcards (${cards.length})`}>
      {cards.length === 0 ? (
        <Empty label="Waiting for flashcards…" />
      ) : (
        <ul className="flex flex-col gap-2">
          {cards.map(({ key, value }) => (
            <li key={key} className="rounded-md border border-zinc-200 p-3">
              <p className="text-sm font-medium text-zinc-900">{value.front}</p>
              <p className="mt-1 text-sm text-zinc-600">{value.back}</p>
              {value.hint ? (
                <p className="mt-2 text-xs text-zinc-500">Hint: {value.hint}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function QuizPanel() {
  const questions = useRunPayloads<QuizQuestion>("custom:quiz_question");

  return (
    <Panel title={`Quiz (${questions.length})`}>
      {questions.length === 0 ? (
        <Empty label="Waiting for quiz…" />
      ) : (
        <ol className="flex flex-col gap-2">
          {questions.map(({ key, value }) => (
            <li key={key} className="rounded-md border border-zinc-200 p-3">
              <p className="text-sm font-medium text-zinc-900">
                {value.question}
              </p>
              <ul className="mt-1 flex flex-col gap-0.5">
                {value.options?.map((option) => (
                  <li
                    key={option}
                    className={
                      option === value.answer
                        ? "text-sm font-medium text-green-700"
                        : "text-sm text-zinc-600"
                    }
                  >
                    {option}
                  </li>
                ))}
              </ul>
              {value.explanation ? (
                <p className="mt-2 text-xs text-zinc-500">
                  {value.explanation}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}
