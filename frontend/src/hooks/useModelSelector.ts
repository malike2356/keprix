"use client";

import useSWR from "swr";
import { fetchAvailableModels } from "@/lib/model-api";
import { useResolvedModel } from "@/hooks/useChat";

export function useModelSelector() {
  const { data: models = [], isLoading } = useSWR("workspace-models", fetchAvailableModels);
  const [modelId, selectModel] = useResolvedModel(models);
  const active = models.find((item) => item.id === modelId) || models[0] || null;
  return { models, modelId, active, selectModel, isLoading };
}
