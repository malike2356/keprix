"use client";

import { Mic } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

export type AIVoiceInputProps = {
  /**
   * Controlled recording flag. When provided, the parent owns start/stop timing
   * via `onToggle` and `elapsedSeconds` (production path for web chat).
   */
  recording?: boolean;
  elapsedSeconds?: number;
  onToggle?: () => void;
  onStart?: () => void;
  onStop?: (duration: number) => void;
  visualizerBars?: number;
  /** Autoplay demo loop; dev/Storybook only. */
  demoMode?: boolean;
  demoInterval?: number;
  className?: string;
  disabled?: boolean;
  ariaLabel?: string;
};

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function visualizerHeight(index: number, elapsedSeconds: number) {
  const wave = Math.sin((index + elapsedSeconds) * 0.45) * 0.5 + 0.5;
  return `${20 + wave * 80}%`;
}

/**
 * Push-to-talk voice input visualizer. Prefer controlled mode (`recording`,
 * `elapsedSeconds`, `onToggle`) when wired to `useWebVoiceRecorder`.
 */
export function AIVoiceInput({
  recording,
  elapsedSeconds = 0,
  onToggle,
  onStart,
  onStop,
  visualizerBars = 48,
  demoMode = false,
  demoInterval = 3000,
  className,
  disabled = false,
  ariaLabel,
}: AIVoiceInputProps) {
  const isControlled = recording !== undefined;
  const [internalActive, setInternalActive] = React.useState(false);
  const [internalTime, setInternalTime] = React.useState(0);
  const [isDemo, setIsDemo] = React.useState(demoMode);
  const durationRef = React.useRef(0);
  const wasActiveRef = React.useRef(false);

  const isActive = isControlled ? Boolean(recording) : internalActive;
  const displayTime = isControlled ? elapsedSeconds : internalTime;

  React.useEffect(() => {
    if (isControlled || !internalActive) {
      return;
    }
    const intervalId = window.setInterval(() => {
      setInternalTime((value) => {
        const next = value + 1;
        durationRef.current = next;
        return next;
      });
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [internalActive, isControlled]);

  React.useEffect(() => {
    if (isControlled) {
      return;
    }
    if (internalActive && !wasActiveRef.current) {
      onStart?.();
    }
    if (!internalActive && wasActiveRef.current) {
      onStop?.(durationRef.current);
      durationRef.current = 0;
      setInternalTime(0);
    }
    wasActiveRef.current = internalActive;
  }, [internalActive, isControlled, onStart, onStop]);

  React.useEffect(() => {
    if (!isDemo || isControlled) {
      return;
    }

    let timeoutId: number | undefined;
    const runAnimation = () => {
      setInternalActive(true);
      timeoutId = window.setTimeout(() => {
        setInternalActive(false);
        timeoutId = window.setTimeout(runAnimation, 1000);
      }, demoInterval);
    };

    const initialTimeout = window.setTimeout(runAnimation, 100);
    return () => {
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
      window.clearTimeout(initialTimeout);
    };
  }, [demoInterval, isControlled, isDemo]);

  const handleClick = () => {
    if (disabled) {
      return;
    }
    if (isDemo) {
      setIsDemo(false);
      setInternalActive(false);
      return;
    }
    if (isControlled) {
      onToggle?.();
      return;
    }
    setInternalActive((prev) => !prev);
  };

  const label =
    ariaLabel ?? (isActive ? "Stop recording" : disabled ? "Voice input unavailable" : "Start voice input");

  return (
    <div className={cn("w-full py-4", className)}>
      <div className="relative max-w-xl w-full mx-auto flex items-center flex-col gap-2">
        <button
          className={cn(
            "group w-16 h-16 rounded-xl flex items-center justify-center transition-colors",
            disabled ? "cursor-not-allowed opacity-50" : "hover:bg-[var(--kp-voice-hover)]",
          )}
          type="button"
          onClick={handleClick}
          disabled={disabled}
          aria-label={label}
          aria-pressed={isActive}
        >
          {isActive ? (
            <div
              className="w-6 h-6 rounded-sm animate-spin bg-[var(--kp-voice-indicator)] cursor-pointer pointer-events-auto"
              style={{ animationDuration: "3s" }}
            />
          ) : (
            <Mic className="w-6 h-6 text-[var(--kp-voice-text-muted)]" aria-hidden />
          )}
        </button>

        <span
          className={cn(
            "font-mono text-sm transition-opacity duration-300",
            isActive ? "text-[var(--kp-voice-text-muted)]" : "text-[var(--kp-voice-text-faint)]",
          )}
          aria-live="polite"
        >
          {formatTime(displayTime)}
        </span>

        <div className="h-4 w-64 flex items-center justify-center gap-0.5" aria-hidden>
          {Array.from({ length: visualizerBars }).map((_, index) => (
            <div
              key={index}
              className={cn(
                "w-0.5 rounded-full transition-all duration-300",
                isActive
                  ? "bg-[var(--kp-voice-bar-active)] animate-pulse"
                  : "bg-[var(--kp-voice-bar-idle)] h-1",
              )}
              style={
                isActive
                  ? {
                      height: visualizerHeight(index, displayTime),
                      animationDelay: `${index * 0.05}s`,
                    }
                  : undefined
              }
            />
          ))}
        </div>

        <p className="h-4 text-xs text-[var(--kp-voice-text-muted)]">
          {disabled ? "Voice input unavailable" : isActive ? "Listening..." : "Click to speak"}
        </p>
      </div>
    </div>
  );
}
