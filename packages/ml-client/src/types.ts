export interface EmbedRequest {
  texts: string[];
  model?: string;
  pack_id?: string;
}

export interface EmbedResponse {
  embeddings: number[][];
  model: string;
  token_count: number;
}

export interface SearchRequest {
  query: string;
  pack_id: string;
  top_k?: number;
  score_threshold?: number;
}

export interface SearchResult {
  content: string;
  score: number;
  source_uri: string;
  chunk_index: number;
  metadata: Record<string, unknown>;
}

export interface KnowledgePack {
  pack_id: string;
  display_name: string;
  description?: string;
  chunk_count: number;
  indexed_at?: string | null;
}

export interface DetectLanguageRequest {
  text: string;
}

export interface DetectLanguageResponse {
  language: string;
  confidence: number;
  script: string;
}

export interface TranslateRequest {
  text: string;
  src_lang: string;
  tgt_lang: string;
}

export interface TranslateResponse {
  translated_text: string;
  src_lang: string;
}

export interface TranscribeRequest {
  audio_b64: string;
  mime_type: string;
  language?: string;
}

export interface TranscribeResponse {
  text: string;
  detected_language?: string;
}

export interface SynthesizeSpeechRequest {
  text: string;
  language?: string;
  voice_id?: string;
}

export interface SynthesizeSpeechResponse {
  audio_b64: string;
  mime_type: string;
}

export interface ClassifyIntentRequest {
  text: string;
  context?: string;
}

export interface ClassifyIntentResponse {
  intent: string;
  confidence: number;
  model: string;
}

export interface ClassifyFormationRequest {
  description: string;
}

export interface ClassifyFormationResponse {
  formation: string;
  confidence: number;
  model: string;
}

export interface PredictYieldRequest {
  formation: string;
  depth_m: number;
  gps_lat?: number;
  gps_lng?: number;
}

export interface PredictYieldResponse {
  yield_class: string;
  confidence: number;
  model: string;
}

export interface DuplicateMemberRequest {
  first_name: string;
  last_name: string;
  phone?: string;
  dob?: string;
}

export interface DuplicateMemberResponse {
  is_likely_duplicate: boolean;
  candidates: Array<{
    member_id: string;
    full_name: string;
    phone: string;
    similarity_score: number;
    match_reason: string;
  }>;
}

export interface AnomalyRequest {
  agent_id: string;
  action_sequence: string[];
}

export interface AnomalyResponse {
  agent_id: string;
  anomaly_score: number;
  is_anomalous: boolean;
  similar_past_sequences: string[];
  explanation: string;
}

export interface MLServiceHealth {
  status: "ok" | "degraded" | "down";
  providers: Record<string, "ok" | "unavailable">;
  models_loaded: string[];
}
