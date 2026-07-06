"use client";

import * as React from "react";
import useSWR from "swr";
import { fetchAudioStatus, transcribeAudioBlob } from "@/lib/audio-api";
import { useMicRecorder } from "@/hooks/useMicRecorder";
import { fetchUiContract } from "@/lib/ui-contract";

export type WebVoiceStatus = "idle" | "recording" | "transcribing";

export type UseWebVoiceRecorderOptions = {
  maxRecordingSeconds?: number;
  onTranscript: (text: string) => void;
  onError?: (message: string) => void;
  /** When false (e.g. agent streaming), recording is disabled. */
  enabled?: boolean;
};

const EMPTY_TRANSCRIPT_MESSAGE = "No speech detected. Try recording again.";

export function useWebVoiceRecorder({
  maxRecordingSeconds,
  onTranscript,
  onError,
  enabled = true,
}: UseWebVoiceRecorderOptions) {
  const { data: audioStatus } = useSWR("audio-status", fetchAudioStatus, {
    revalidateOnFocus: true,
  });
  const { data: uiContract } = useSWR("ui-contract", fetchUiContract, {
    revalidateOnFocus: false,
  });

  const mic = useMicRecorder();
  const [status, setStatus] = React.useState<WebVoiceStatus>("idle");
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0);

  const startedAtRef = React.useRef(0);
  const intervalRef = React.useRef<number | null>(null);
  const timeoutRef = React.useRef<number | null>(null);
  const stopRef = React.useRef<() => Promise<void>>(async () => {});

  const voiceInputEnabled = uiContract?.feature_flags?.voice_input !== false;
  const sttAvailable = (audioStatus?.stt_enabled ?? false) && voiceInputEnabled;
  const maxSeconds = React.useMemo(() => {
    const configured = maxRecordingSeconds ?? audioStatus?.max_recording_seconds ?? 120;
    return Math.max(1, Math.min(Math.trunc(configured), 600));
  }, [audioStatus?.max_recording_seconds, maxRecordingSeconds]);

  const clearTimers = React.useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  React.useEffect(() => () => clearTimers(), [clearTimers]);

  const finishRecording = React.useCallback(async () => {
    clearTimers();
    const result = await mic.stop();
    if (!result) {
      setStatus("idle");
      setElapsedSeconds(0);
      return;
    }

    setStatus("transcribing");
    try {
      const response = await transcribeAudioBlob(result.audio);
      const transcript = response.transcript.trim();
      if (!transcript) {
        onError?.(EMPTY_TRANSCRIPT_MESSAGE);
      } else {
        onTranscript(transcript);
      }
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Transcription failed");
    } finally {
      setStatus("idle");
      setElapsedSeconds(0);
    }
  }, [clearTimers, mic, onError, onTranscript]);

  stopRef.current = finishRecording;

  const startRecording = React.useCallback(async () => {
    if (!enabled) {
      return;
    }
    if (!sttAvailable) {
      onError?.("Speech-to-text is disabled on this instance.");
      return;
    }
    if (status !== "idle") {
      return;
    }

    try {
      await mic.start();
      startedAtRef.current = Date.now();
      setElapsedSeconds(0);
      setStatus("recording");
      intervalRef.current = window.setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000));
      }, 250);
      timeoutRef.current = window.setTimeout(() => {
        void stopRef.current();
      }, maxSeconds * 1000);
    } catch (err) {
      setStatus("idle");
      setElapsedSeconds(0);
      onError?.(err instanceof Error ? err.message : "Could not start recording");
    }
  }, [enabled, maxSeconds, mic, onError, status, sttAvailable]);

  const toggle = React.useCallback(() => {
    if (!enabled) {
      return;
    }
    if (status === "recording") {
      void finishRecording();
      return;
    }
    if (status === "idle") {
      void startRecording();
    }
  }, [enabled, finishRecording, startRecording, status]);

  const cancel = React.useCallback(() => {
    if (status !== "recording") {
      return;
    }
    clearTimers();
    mic.cancel();
    setStatus("idle");
    setElapsedSeconds(0);
  }, [clearTimers, mic, status]);

  return {
    status,
    elapsedSeconds,
    level: mic.level,
    toggle,
    cancel,
    sttAvailable,
    micError: mic.error,
  };
}
