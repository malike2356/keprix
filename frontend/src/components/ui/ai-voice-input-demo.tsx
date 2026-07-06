"use client";

import * as React from "react";
import { AIVoiceInput } from "@/components/ui/ai-voice-input";

export function AIVoiceInputDemo() {
  const [recordings, setRecordings] = React.useState<{ duration: number; timestamp: Date }[]>([]);

  const handleStop = (duration: number) => {
    setRecordings((prev) => [...prev.slice(-4), { duration, timestamp: new Date() }]);
  };

  return (
    <div className="kp-voice-root space-y-8">
      <div className="space-y-4">
        <AIVoiceInput onStart={() => undefined} onStop={handleStop} visualizerBars={32} />
      </div>
      {recordings.length > 0 ? (
        <ul className="text-sm text-[var(--kp-voice-text-muted)] space-y-1">
          {recordings.map((entry, index) => (
            <li key={`${entry.timestamp.toISOString()}-${index}`}>
              Recorded {entry.duration}s at {entry.timestamp.toLocaleTimeString()}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
