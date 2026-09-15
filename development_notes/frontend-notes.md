# Frontend notes

## Profiling: `StableStreamContext` boundary

### Background

Every component that calls `useStreamContext()` subscribes to the root stream
snapshot, which is rewritten on every flush while tokens stream. Components that
only read one custom channel therefore wake for traffic they never render.

`StableStreamContext` is a boundary component: it consumes the churning context
once, holds the handle in a ref so its identity never changes, and republishes
it. `children` arrives as an unchanged element reference, so React bails out of
the subtree and the leaves wake only for their own channel.

### Setup

Four panels, each subscribing to one channel via `useChannel`
(`custom:flashcard`, `custom:quiz_question`, `lifecycle`, `values`). One full
graph run per measurement: notes, quiz, flashcards and deep dive, producing
~2350 message-channel events. Three runs per variant. Chrome metrics captured
over the Chrome DevTools Protocol, React commit data from `<Profiler>`.

### Results

| Metric                  | Without StableStream | With StableStream |
| ----------------------- | -------------------- | ----------------- |
| Render passes per panel | 2279                 | 14                |
| Commits                 | 17                   | 17                |
| Committed render time   | 3.7 ms               | 3.8 ms            |
| Script duration         | 1.38 s               | 1.31 s            |
| Task duration           | 2.56 s               | 2.62 s            |

Per-run spread: script duration ranged 1.32-1.49 s without the boundary and
1.24-1.43 s with it.

### Reading

The 163x reduction in render passes produced no measurable saving. The two
script-duration ranges overlap almost entirely, and task duration came out
marginally higher *with* the boundary, which is noise pointing the other way.

The commits row explains it. It is 17 either way, because the panels rendered
identical output and React refused to commit the redundant passes. Those extra
passes are function calls plus reconciliation of a one-line tree; they never
reach the DOM. Layout and style recalculation were effectively zero throughout.

The ~1.3 s of scripting is the SDK's own work: parsing SSE frames, assembling
messages, updating the root store on each flush. That cost is independent of how
many panels are mounted, and context isolation does not touch it.

### Caveat

The panels under test rendered `<div>A:5</div>`. At that size a render pass costs
well under 10 µs, which is why ~9000 of them disappear into the noise floor. This
result is specific to component size, not a general claim that context churn is
free.

### Action

Do not adopt `StableStreamContext` on the strength of render counts alone. The
count is real; the cost is not, at this component size.

**Revisit once the full implementation is in place and re-run the profiler.**
Panels rendering real content — streamed markdown, long flashcard lists — cost
meaningfully more per pass, and the two variants may then separate. The decision
should be made against that measurement, not this one.

### Related

Bandwidth is the axis with a measurable cost. Roughly 89% of stream traffic is
message-channel token deltas. Panels that consume only custom channels ignore all
of it. That fix belongs server-side in `_publish`, not in React.

---

## Profiling round 2: four real panels

Re-run of the above against a real implementation, as the previous section asked
for. **This is still a partial implementation**, so treat it as directional.

### Setup

Four panels in a 2x2 grid. Notes and deep dive reassemble their node's text from
raw `content-block-delta` frames and render it as markdown via `react-markdown`
while it streams. Flashcards and quiz read their `custom:` channels. One graph
run per measurement, three runs per variant.

### Results

| Metric                        | Without StableStream | With StableStream |
| ----------------------------- | -------------------- | ----------------- |
| Script duration               | 25.07 s              | 26.91 s           |
| Task duration                 | 25.93 s              | 27.78 s           |
| Commits                       | 2758                 | 2816              |
| Committed render time         | 21.3 s               | 24.3 s            |
| Render passes, notes / deep   | 5577                 | 5611              |
| Render passes, cards / quiz   | 50-170               | 18                |

### Reading

The boundary still does exactly what it is designed to do. The flashcard and quiz
panels drop to 18 passes. It still buys nothing, and the reason has changed.

The cost now sits entirely in the notes and deep dive panels, and their renders
are driven by their **own** `messages` subscription, not by context churn. The
boundary cannot touch a panel's own channel. It only silences unrelated wakeups,
and the panels being woken unnecessarily were the two cheap ones.

So the earlier conclusion holds for a new reason. Isolating context churn helps
only when a panel is expensive *and* subscribed to something quiet. Here the
expensive panels are subscribed to the noisiest channel by design.

### The actual bottleneck

A diagnostic run with `react-markdown` swapped for a plain text node, everything
else identical:

| Variant             | Script duration | Committed render time |
| ------------------- | --------------- | --------------------- |
| Markdown            | 25.07 s         | 21.3 s                |
| Plain text          | 3.93 s          | 1.09 s                |

Markdown accounts for roughly 85% of total scripting. The whole document is
re-parsed on every token, ~2800 times per run, and the main thread stays pegged
for the duration.

Worth trying, in rough order of effort:

1. Throttle markdown re-parsing to a fixed interval (~100 ms) rather than every
   token, and render the tail as plain text between parses.
2. Split the text on completed block boundaries, memoize parsed blocks, and only
   re-parse the final incomplete one.
3. Stream plain text and parse markdown once on `message-finish`.

### Action

`StableStreamContext` is not the lever. Do not adopt it for performance. Revisit
only if a panel becomes expensive while subscribed to a low-frequency channel,
which is the shape it actually helps.
