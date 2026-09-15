"use client";

import { useRouter } from "next/navigation";

export default function StartButton() {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.push(`/thread/${crypto.randomUUID()}`)}
      className="rounded-md bg-black px-6 py-2 text-white"
    >
      Start
    </button>
  );
}
