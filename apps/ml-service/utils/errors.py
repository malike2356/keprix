class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int = 502):
        self.provider = provider
        self.message = message
        self.status_code = status_code
        super().__init__(f"{provider}: {message}")


class ModelNotReadyError(Exception):
    pass


class UnsupportedLanguageError(Exception):
    pass


class ClassifierNotTrainedError(Exception):
    pass
