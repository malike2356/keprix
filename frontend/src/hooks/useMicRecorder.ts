"use client";

import * as React from "react";
import { mapMicrophoneError } from "@/lib/mic-permissions";

type BrowserAudioContext = typeof AudioContext;

const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/ogg",
  "audio/wav",
];

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "";
  }
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? "";
}

export function useMicRecorder() {
  const [level, setLevel] = React.useState(0);
  const [recording, setRecording] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const animationRef = React.useRef<number | null>(null);
  const stopResolverRef = React.useRef<((value: { audio: Blob } | null) => void) | null>(null);

  const cleanup = React.useCallback(() => {
    if (animationRef.current !== null) {
      window.cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setLevel(0);
    setRecording(false);
  }, []);

  React.useEffect(() => () => cleanup(), [cleanup]);

  const startMeter = React.useCallback((stream: MediaStream) => {
    const audioWindow = window as Window & { webkitAudioContext?: BrowserAudioContext };
    const AudioContextCtor = window.AudioContext || audioWindow.webkitAudioContext;
    if (!AudioContextCtor) {
      return;
    }

    try {
      const audioContext = new AudioContextCtor();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      analyser.fftSize = 256;
      const data = new Uint8Array(analyser.fftSize);
      source.connect(analyser);
      audioContextRef.current = audioContext;

      const tick = () => {
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (const value of data) {
          const centered = value - 128;
          sum += centered * centered;
        }
        const rms = Math.sqrt(sum / data.length);
        setLevel(Math.min(1, rms / 42));
        animationRef.current = window.requestAnimationFrame(tick);
      };

      tick();
    } catch {
      setLevel(0);
    }
  }, []);

  const start = React.useCallback(async () => {
    setError(null);
    if (recorderRef.current) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      const message = "Microphone recording is not supported in this browser.";
      setError(message);
      throw new Error(message);
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch (err) {
      const message = mapMicrophoneError(err);
      setError(message);
      throw new Error(message);
    }

    const mimeType = pickMimeType();
    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    } catch (err) {
      stream.getTracks().forEach((track) => track.stop());
      const message = mapMicrophoneError(err);
      setError(message);
      throw new Error(message);
    }

    chunksRef.current = [];
    streamRef.current = stream;
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      const chunks = chunksRef.current;
      const recordingType = recorder.mimeType || mimeType || "audio/webm";
      chunksRef.current = [];
      cleanup();
      const resolver = stopResolverRef.current;
      stopResolverRef.current = null;
      if (!chunks.length) {
        resolver?.(null);
        return;
      }
      resolver?.({ audio: new Blob(chunks, { type: recordingType }) });
    };

    recorder.onerror = (event) => {
      const message = mapMicrophoneError((event as Event & { error?: unknown }).error);
      setError(message);
      const resolver = stopResolverRef.current;
      stopResolverRef.current = null;
      cleanup();
      resolver?.(null);
    };

    recorder.start();
    setRecording(true);
    startMeter(stream);
  }, [cleanup, startMeter]);

  const stop = React.useCallback(() => {
    return new Promise<{ audio: Blob } | null>((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        cleanup();
        resolve(null);
        return;
      }
      stopResolverRef.current = resolve;
      recorder.stop();
    });
  }, [cleanup]);

  const cancel = React.useCallback(() => {
    const recorder = recorderRef.current;
    const resolver = stopResolverRef.current;
    stopResolverRef.current = null;
    if (recorder && recorder.state !== "inactive") {
      recorder.ondataavailable = null;
      recorder.onerror = null;
      recorder.onstop = null;
      recorder.stop();
    }
    cleanup();
    resolver?.(null);
  }, [cleanup]);

  return {
    recording,
    level,
    start,
    stop,
    cancel,
    error,
  };
}
