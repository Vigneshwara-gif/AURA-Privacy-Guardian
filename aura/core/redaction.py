"""
Redaction of sensitive values before they reach a log file.

The user's constraint is explicit: never log passwords, API keys, tokens or
private communications. Relying on developers to remember that at every call
site does not work — the failure is silent and permanent, because once a
secret is written to a rotating log file it has leaked.

So redaction is enforced at the logging boundary instead, by a
``logging.Filter`` attached to every handler. A developer who logs an
exception whose message happens to contain a connection string still gets a
redacted log line.

Two design rules:

  * **Never raise.** A filter that throws breaks logging, and broken logging
    during an incident is worse than a verbose log. Every entry point is
    wrapped, and on failure the filter returns the record unchanged rather
    than dropping it — losing an event is worse than logging it unredacted,
    because a dropped security event is invisible.

  * **Redact, do not delete.** Usernames inside Windows paths are replaced in
    place, so ``C:\\Users\\alice\\Documents\\report.docx`` becomes
    ``C:\\Users\\<user>\\Documents\\report.docx``. The path stays useful for
    debugging while the account name is removed.

This module intentionally depends only on the standard library so it can be
installed before configuration is loaded.

Honest limitation: this is pattern-based and therefore incomplete. It reliably
catches conventional ``key=value`` secrets, bearer tokens, JWTs, connection
strings and long hex blobs. It cannot catch a bare secret logged with no
surrounding context — ``logger.info(api_key)`` produces an opaque string with
nothing to match on. Redaction is a safety net, not a licence to log secrets.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

__all__ = [
    "REDACTED",
    "Redactor",
    "RedactionFilter",
    "redact",
    "install_redaction",
]

REDACTED: Final = "[REDACTED]"
REDACTED_HEX: Final = "[REDACTED:HEX]"
REDACTED_JWT: Final = "[REDACTED:JWT]"
USER_PLACEHOLDER: Final = "<user>"

# Keys whose values must never appear in a log.
_SENSITIVE_KEY_NAMES: Final = (
    "password",
    "passwd",
    "pwd",
    "passphrase",
    "secret",
    "client_secret",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "api-key",
    "access_key",
    "secret_key",
    "private_key",
    "authorization",
    "auth",
    "bearer",
    "credential",
    "credentials",
    "session_id",
    "sessionid",
    "cookie",
    "set-cookie",
    "csrf",
    "otp",
    "pin",
)

# Sorted longest-first so that ``refresh_token`` is matched before ``token``,
# which keeps the more specific key name in the output.
_KEY_ALTERNATION: Final = "|".join(
    re.escape(name) for name in sorted(_SENSITIVE_KEY_NAMES, key=len, reverse=True)
)

# ----------------------------------------------------------------------
# Patterns
# ----------------------------------------------------------------------
# Ordered: more specific patterns first, so a URL credential is handled as a
# URL credential rather than being partly consumed by the generic key/value
# rule.

_ALWAYS_ON: Final[tuple[tuple[str, re.Pattern[str], str], ...]] = (
    (
        # Credentials embedded in a URL or DSN: scheme://user:password@host
        "url_credentials",
        re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.\-]*://)(?P<user>[^:/@\s]+):[^@\s/]+@"),
        r"\g<scheme>\g<user>:" + REDACTED + "@",
    ),
    (
        # JWTs are self-identifying: the header almost always starts "eyJ".
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]*"),
        REDACTED_JWT,
    ),
    (
        # Authorization header values, including the scheme keyword.
        "auth_scheme",
        re.compile(r"(?i)\b(?P<scheme>Bearer|Basic|Digest|Token|ApiKey)\s+[A-Za-z0-9._\-+/=]{8,}"),
        r"\g<scheme> " + REDACTED,
    ),
    (
        # PEM private key blocks. Redacts the whole block, not just the header.
        "pem_block",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        REDACTED,
    ),
    (
        # key=value / "key": "value" / key: value
        "key_value",
        re.compile(
            r"(?i)(?P<key>\b(?:" + _KEY_ALTERNATION + r")\b)"
            r"(?P<sep>[\"']?\s*[:=]\s*[\"']?)"
            r"(?P<value>[^\s\"',;)\}\]&]+)"
        ),
        r"\g<key>\g<sep>" + REDACTED,
    ),
    (
        # Long hexadecimal runs: session identifiers, hashes, raw key material.
        # 32 is the length of an MD5 hex digest, which is the shortest value in
        # this family worth suppressing.
        "hex_blob",
        re.compile(r"\b[0-9a-fA-F]{32,}\b"),
        REDACTED_HEX,
    ),
)

_USER_PATH_PATTERNS: Final[tuple[tuple[str, re.Pattern[str], str], ...]] = (
    (
        "windows_user_path",
        re.compile(r"(?i)(?P<prefix>[A-Za-z]:[\\/]Users[\\/])(?P<name>[^\\/\s\"',;)\]]+)"),
        r"\g<prefix>" + USER_PLACEHOLDER,
    ),
    (
        "unc_user_path",
        re.compile(r"(?i)(?P<prefix>\\\\[^\\]+\\Users\\)(?P<name>[^\\/\s\"',;)\]]+)"),
        r"\g<prefix>" + USER_PLACEHOLDER,
    ),
    (
        "posix_home_path",
        re.compile(r"(?P<prefix>/(?:home|Users)/)(?P<name>[^/\s\"',;)\]]+)"),
        r"\g<prefix>" + USER_PLACEHOLDER,
    ),
)


class Redactor:
    """
    Applies the redaction patterns to arbitrary text.

    Stateless and thread-safe once constructed; compiled patterns are shared
    at module level, so creating a Redactor is cheap.
    """

    __slots__ = ("enabled", "redact_user_paths", "_patterns")

    def __init__(self, *, enabled: bool = True, redact_user_paths: bool = True) -> None:
        self.enabled = enabled
        self.redact_user_paths = redact_user_paths
        patterns = list(_ALWAYS_ON)
        if redact_user_paths:
            patterns.extend(_USER_PATH_PATTERNS)
        self._patterns = tuple(patterns)

    def __call__(self, value: Any) -> Any:
        return self.scrub(value)

    def scrub_text(self, text: str) -> str:
        """Redact a single string. Returns the input unchanged on failure."""
        if not self.enabled or not text:
            return text
        try:
            result = text
            for _name, pattern, replacement in self._patterns:
                result = pattern.sub(replacement, result)
            return result
        except Exception:  # noqa: BLE001 - redaction must never break logging
            return text

    def scrub(self, value: Any, _depth: int = 0) -> Any:
        """
        Redact a string, or recursively redact a container of strings.

        Non-string scalars are returned unchanged: an int cannot carry a
        secret, and coercing everything to text would corrupt ``%``-style log
        formatting. Recursion is depth-limited because a self-referential
        structure would otherwise hang the logging call.
        """
        if not self.enabled:
            return value

        if _depth > 4:
            return value

        try:
            if isinstance(value, str):
                return self.scrub_text(value)
            if isinstance(value, dict):
                return {
                    self.scrub(key, _depth + 1): self.scrub(item, _depth + 1)
                    for key, item in value.items()
                }
            # Union form rather than a tuple: satisfies ruff UP038 where that
            # rule is active, and is valid on every supported Python (>=3.11).
            if isinstance(value, list | tuple | set):
                scrubbed = [self.scrub(item, _depth + 1) for item in value]
                if isinstance(value, tuple):
                    return tuple(scrubbed)
                if isinstance(value, set):
                    return set(scrubbed)
                return scrubbed
        except Exception:  # noqa: BLE001 - never break logging
            return value

        return value


# Module-level default, used by the convenience function below.
_DEFAULT_REDACTOR = Redactor()


def redact(value: Any) -> Any:
    """Redact a value using the default settings."""
    return _DEFAULT_REDACTOR.scrub(value)


class RedactionFilter(logging.Filter):
    """
    Logging filter that redacts a record in place before formatting.

    Attach to handlers rather than to loggers. A filter on a logger is not
    consulted for records that propagate up from child loggers, which would
    leave third-party log output unredacted — precisely the output most likely
    to contain a connection string.

    Mutating the record is intentional and safe to repeat: the replacements
    are idempotent, so a record passing through two redacting handlers is not
    corrupted.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        redact_user_paths: bool = True,
        name: str = "",
    ) -> None:
        super().__init__(name)
        self.redactor = Redactor(enabled=enabled, redact_user_paths=redact_user_paths)

    # `filter` is the stdlib logging.Filter API name.
    def filter(self, record: logging.LogRecord) -> bool:
        if not self.redactor.enabled:
            return True

        try:
            if isinstance(record.msg, str):
                record.msg = self.redactor.scrub_text(record.msg)

            if record.args:
                record.args = self.redactor.scrub(record.args)  # type: ignore[assignment]

            # Exception text is a common leak path: a database driver's error
            # message frequently embeds the full DSN.
            if record.exc_text:
                record.exc_text = self.redactor.scrub_text(record.exc_text)

            if getattr(record, "stack_info", None):
                record.stack_info = self.redactor.scrub_text(str(record.stack_info))

            # Structured extras added via logger.info(..., extra={...}).
            extra = getattr(record, "aura_extra", None)
            if isinstance(extra, dict):
                record.aura_extra = self.redactor.scrub(extra)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            # Returning True keeps the record. An unredacted line is bad; a
            # silently dropped security event is worse.
            return True

        return True


def install_redaction(
    handler: logging.Handler,
    *,
    enabled: bool = True,
    redact_user_paths: bool = True,
) -> None:
    """Attach a RedactionFilter to a handler, avoiding duplicates."""
    for existing in handler.filters:
        if isinstance(existing, RedactionFilter):
            existing.redactor = Redactor(
                enabled=enabled, redact_user_paths=redact_user_paths
            )
            return
    handler.addFilter(
        RedactionFilter(enabled=enabled, redact_user_paths=redact_user_paths)
    )
