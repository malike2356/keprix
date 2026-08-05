import { MLServiceClientBase } from "./base-client";
import type {
  ClassifyFormationRequest,
  ClassifyFormationResponse,
  ClassifyIntentRequest,
  ClassifyIntentResponse,
  DuplicateMemberRequest,
  DuplicateMemberResponse,
  AnomalyRequest,
  AnomalyResponse,
  PredictYieldRequest,
  PredictYieldResponse,
} from "./types";

export class ClassifierClient extends MLServiceClientBase {
  classifyIntent(request: ClassifyIntentRequest): Promise<ClassifyIntentResponse> {
    return this.post<ClassifyIntentResponse>("/classifiers/intent", request);
  }

  classifyFormation(request: ClassifyFormationRequest): Promise<ClassifyFormationResponse> {
    return this.post<ClassifyFormationResponse>("/classifiers/formation", request);
  }

  predictYield(request: PredictYieldRequest): Promise<PredictYieldResponse> {
    return this.post<PredictYieldResponse>("/classifiers/yield", request);
  }

  checkDuplicate(request: DuplicateMemberRequest): Promise<DuplicateMemberResponse> {
    return this.post<DuplicateMemberResponse>("/classifiers/duplicate", request);
  }

  detectAnomaly(request: AnomalyRequest): Promise<AnomalyResponse> {
    return this.post<AnomalyResponse>("/classifiers/anomaly", request);
  }

  reloadModels(): Promise<{ intent: boolean; formation: boolean; yield: boolean }> {
    return this.post<{ intent: boolean; formation: boolean; yield: boolean }>("/classifiers/reload", {});
  }
}
