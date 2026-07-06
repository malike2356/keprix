"use client";

import { AIVoiceInput } from "@/components/ui/ai-voice-input";

export type ChatVoiceControlProps = {
  isRecording: boolean;
  elapsedSeconds: number;
  disabled?: boolean;
  onToggleRecording: () => void;
};

/**
 * MUI-safe bridge into the Tailwind voice island for chat composer integration.
 */
export default function ChatVoiceControl({
  isRecording,
  elapsedSeconds,
  disabled = false,
  onToggleRecording,
}: ChatVoiceControlProps) {
  return (
    <div className="kp-voice-root">
      <AIVoiceInput
        className="py-0"
        visualizerBars={24}
        recording={isRecording}
        elapsedSeconds={elapsedSeconds}
        onToggle={onToggleRecording}
        disabled={disabled}
        ariaLabel={isRecording ? "Stop recording" : "Start voice input"}
      />
    </div>
  );
}
