// import {
//   StreamProvider,
//   useStreamContext,
//   HttpAgentServerAdapter,
//   useExtension,
// } from "@langchain/react";

// export default async function ThreadPage({
//   params,
// }: PageProps<"/thread/[threadId]">) {
//   const { threadId } = await params;

//   const transport = new HttpAgentServerAdapter({
//     apiUrl: "http://localhost:8000",
//     threadId: threadId,
//     paths: {
//       commands: (threadId) => `/api/threads/${threadId}/commands`,
//       stream: (threadId) => `/api/threads/${threadId}/stream`,
//     },
//   });

//   return (
//     <StreamProvider transport={transport}>
//       <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans text-black">
//         <p>{threadId}</p>
//         <FlashCards />
//       </div>
//     </StreamProvider>
//   );
// }

// function FlashCard({ fStream }: { fStream: any }) {
//   return (
//     <div>
//       <pre>{fStream}</pre>
//     </div>
//   );
// }

// function FlashCards() {
//   const stream = useStreamContext();
//   const flashcards: any = useExtension(stream, "flashcard");
//   return flashcards.map((f: any, i: any) => <FlashCard key={i} fStream={f} />);
// }

import ThreadClient from "./ThreadClient";

export default async function ThreadPage({
  params,
}: PageProps<"/thread/[threadId]">) {
  const { threadId } = await params;

  return <ThreadClient threadId={threadId} />;
}
