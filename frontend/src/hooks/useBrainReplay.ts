"use client";

import * as React from "react";
import type { SessionReplayData } from "@/types/brain-replay";

const EMPTY_MESSAGES: SessionReplayData["messages"] = [];
const EMPTY_ACTIVATIONS: SessionReplayData["activations"] = [];

function nodeKey(kind: string, id: string): string {
  return `${kind}:${id}`;
}

function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const value of a) {
    if (!b.has(value)) return false;
  }
  return true;
}

export function useBrainReplay(replayData: SessionReplayData | null) {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [playing, setPlaying] = React.useState(false);
  const [speed, setSpeed] = React.useState<1 | 2 | 4>(1);
  const [activeNodeIds, setActiveNodeIds] = React.useState<Set<string>>(new Set());

  const messages = replayData?.messages ?? EMPTY_MESSAGES;
  const activations = replayData?.activations ?? EMPTY_ACTIVATIONS;

  React.useEffect(() => {
    setCurrentStep(0);
    setPlaying(false);
    setActiveNodeIds((previous) => (previous.size === 0 ? previous : new Set()));
  }, [replayData?.session_id]);

  const currentActivations = React.useMemo(
    () => activations.filter((activation) => activation.step === currentStep),
    [activations, currentStep],
  );

  const currentMessage = messages[currentStep] ?? null;

  React.useEffect(() => {
    if (!playing || messages.length === 0) return;
    const timer = window.setInterval(() => {
      setCurrentStep((step) => {
        if (step >= messages.length - 1) {
          setPlaying(false);
          return step;
        }
        return step + 1;
      });
    }, 1500 / speed);
    return () => window.clearInterval(timer);
  }, [messages.length, playing, speed]);

  React.useEffect(() => {
    const message = messages[currentStep];
    const ids = new Set<string>(
      currentActivations.map((activation) => nodeKey(activation.node_kind, activation.node_id)),
    );
    if (message) {
      for (const key of [...message.activations_before, ...message.activations_during]) ids.add(key);
    }
    setActiveNodeIds((previous) => (sameSet(previous, ids) ? previous : ids));
    if (!playing) return;
    const timer = window.setTimeout(() => {
      setActiveNodeIds((previous) => (previous.size === 0 ? previous : new Set()));
    }, 2500);
    return () => window.clearTimeout(timer);
  }, [currentActivations, currentStep, messages, playing]);

  return {
    currentStep,
    totalSteps: messages.length,
    currentMessage,
    currentActivations,
    activeNodeIds,
    playing,
    speed,
    play: () => setPlaying(true),
    pause: () => setPlaying(false),
    stepForward: () => setCurrentStep((step) => Math.min(step + 1, Math.max(messages.length - 1, 0))),
    stepBackward: () => setCurrentStep((step) => Math.max(step - 1, 0)),
    jumpTo: (step: number) => setCurrentStep(Math.max(0, Math.min(step, Math.max(messages.length - 1, 0)))),
    setSpeed,
    close: () => {
      setPlaying(false);
      setCurrentStep(0);
      setActiveNodeIds((previous) => (previous.size === 0 ? previous : new Set()));
    },
  };
}
