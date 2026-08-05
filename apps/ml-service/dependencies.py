from services.embedding_service import EmbeddingService
from services.classifier_service import ClassifierService
from services.language_service import LanguageService

_embedding_service: EmbeddingService | None = None
_language_service: LanguageService | None = None
_classifier_service: ClassifierService | None = None


def set_embedding_service(service: EmbeddingService | None) -> None:
    global _embedding_service
    _embedding_service = service


async def get_embedding_service() -> EmbeddingService:
    if _embedding_service is None:
        raise RuntimeError("Embedding service is not initialized")
    return _embedding_service


def set_language_service(service: LanguageService | None) -> None:
    global _language_service
    _language_service = service


async def get_language_service() -> LanguageService:
    if _language_service is None:
        raise RuntimeError("Language service is not initialized")
    return _language_service


def set_classifier_service(service: ClassifierService | None) -> None:
    global _classifier_service
    _classifier_service = service


async def get_classifier_service() -> ClassifierService:
    if _classifier_service is None:
        raise RuntimeError("Classifier service is not initialized")
    return _classifier_service
