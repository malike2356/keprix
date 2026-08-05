"""Runtime transport errors."""


class RuntimeTransportError(Exception):
    """Base runtime transport error."""


class RuntimeTransportUnavailable(RuntimeTransportError):
    """Raised when a selected runtime transport cannot be used."""


class RuntimeTransportTimeout(RuntimeTransportError):
    """Raised when a runtime operation exceeds its latency budget."""


__all__ = ["RuntimeTransportError", "RuntimeTransportTimeout", "RuntimeTransportUnavailable"]
