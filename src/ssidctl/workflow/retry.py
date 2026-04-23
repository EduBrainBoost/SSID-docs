"""Deterministic retry policy for durable workflow steps.

No jitter is applied so that delay values are fully reproducible across audit
replays.  No I/O or sleep is performed here — the module only *computes*
policy values; callers are responsible for any actual waiting.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable, deterministic retry configuration.

    Attributes:
        max_attempts: Maximum total number of attempts allowed (including the
            first attempt).  A value of ``0`` means no retries are permitted at
            all (``should_retry`` will always return ``False``).
        base_delay_seconds: Base delay in seconds used for exponential back-off
            calculation.
        max_delay_seconds: Upper bound on the computed delay in seconds.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0

    def should_retry(self, attempt: int) -> bool:
        """Return ``True`` if another attempt should be made.

        Args:
            attempt: The zero-based index of the attempt that has *just
                completed* (i.e. ``0`` after the first attempt, ``1`` after the
                second, …).

        Returns:
            ``True`` when ``attempt < max_attempts``, ``False`` otherwise.
        """
        return attempt < self.max_attempts

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the deterministic back-off delay before the next attempt.

        Uses exponential back-off without jitter:
            delay = base_delay_seconds * 2 ** attempt

        The result is capped at ``max_delay_seconds``.

        Args:
            attempt: The zero-based index of the attempt that has *just
                completed*.  Passing ``0`` returns ``base_delay_seconds * 1``,
                passing ``1`` returns ``base_delay_seconds * 2``, etc.

        Returns:
            Delay in seconds as a ``float``, capped at ``max_delay_seconds``.
        """
        delay = self.base_delay_seconds * (2**attempt)
        return min(delay, self.max_delay_seconds)
