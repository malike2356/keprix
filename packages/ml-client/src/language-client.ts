import { MLServiceClientBase } from "./base-client";
import type {
  DetectLanguageRequest,
  DetectLanguageResponse,
  SynthesizeSpeechRequest,
  SynthesizeSpeechResponse,
  TranscribeRequest,
  TranscribeResponse,
  TranslateRequest,
  TranslateResponse,
} from "./types";

export class LanguageClient extends MLServiceClientBase {
  detectLanguage(request: DetectLanguageRequest): Promise<DetectLanguageResponse> {
    return this.post<DetectLanguageResponse>("/language/detect", request);
  }

  translate(request: TranslateRequest): Promise<TranslateResponse> {
    return this.post<TranslateResponse>("/language/translate", request);
  }

  transcribe(request: TranscribeRequest): Promise<TranscribeResponse> {
    return this.post<TranscribeResponse>("/language/transcribe", request);
  }

  synthesize(request: SynthesizeSpeechRequest): Promise<SynthesizeSpeechResponse> {
    return this.post<SynthesizeSpeechResponse>("/language/synthesize", request);
  }
}
