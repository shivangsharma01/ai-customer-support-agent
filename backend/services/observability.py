"""LangFuse tracing — enabled only when keys are configured.

Only public state and sanitized tool outputs reach the LLM messages, so traces
sent to LangFuse contain no PII by construction. Tracing must never break the
request path: any failure to initialize disables it with a warning.
"""

import logging
import os

from config import settings

logger = logging.getLogger(__name__)
_handler = None
_failed = False


def get_callbacks() -> list:
    global _handler, _failed
    if _failed or not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return []
    if _handler is None:
        try:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
            os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
            os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
            from langfuse.langchain import CallbackHandler
            _handler = CallbackHandler()
        except Exception as e:  # noqa: BLE001 — tracing is optional, never fatal
            _failed = True
            logger.warning("LangFuse disabled: %s", e)
            return []
    return [_handler]
