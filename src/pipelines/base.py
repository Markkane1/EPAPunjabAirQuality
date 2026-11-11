"""
Clean Architecture base ingestion worker interface.
Adheres to DATA_SOURCES_AND_STREAMS.md §1 & §3, and DATA_PIPELINES_ARCHITECTURE.md §3 & §8.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, List, Optional

from src.pipelines.fallback_engine import FallbackTemplateEngine

logger = logging.getLogger(__name__)


class BaseIngestionWorker(ABC):
    """
    Abstract base worker for external data stream ingestion.
    Coordinates HTTP polling, validation, circuit breaker logic,
    and automatic graceful fallback to the FallbackTemplateEngine.
    """

    def __init__(
        self,
        stream_id: str,
        name: str,
        polling_cadence: str = "hourly",
        fallback_engine: Optional[FallbackTemplateEngine] = None,
        max_failures_before_circuit_break: int = 5,
        circuit_cooldown_seconds: float = 900.0,  # 15 minutes per ARCHITECTURE_OVERVIEW.md §3.1
    ) -> None:
        self.stream_id = stream_id
        self.name = name
        self.polling_cadence = polling_cadence
        self.fallback_engine = fallback_engine or FallbackTemplateEngine()
        self.max_failures_before_circuit_break = max_failures_before_circuit_break
        self.circuit_cooldown_seconds = circuit_cooldown_seconds

        # Operational health telemetry
        self.is_healthy: bool = True
        self.consecutive_failures: int = 0
        self.last_run: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.circuit_breaker_open: bool = False
        self.circuit_breaker_tripped_at: Optional[datetime] = None

    def _check_circuit_breaker(self) -> bool:
        """
        Evaluates whether the circuit breaker should prevent network calls.
        Returns True if circuit is OPEN (blocking live calls), False otherwise.
        """
        if not self.circuit_breaker_open:
            return False

        if self.circuit_breaker_tripped_at is None:
            return False

        now = datetime.now(timezone.utc)
        elapsed = (now - self.circuit_breaker_tripped_at).total_seconds()
        if elapsed > self.circuit_cooldown_seconds:
            # Half-open: allow a trial request
            logger.info("Circuit breaker entering HALF-OPEN state for %s", self.stream_id)
            return False

        logger.warning(
            "Circuit breaker is OPEN for %s (tripped %.0fs ago, cooldown %.0fs). Routing directly to fallback.",
            self.stream_id,
            elapsed,
            self.circuit_cooldown_seconds,
        )
        return True

    @abstractmethod
    async def fetch_data(self, **kwargs: Any) -> Any:
        """Fetch raw payload from external network endpoint."""
        raise NotImplementedError

    @abstractmethod
    def parse_and_validate(self, raw_data: Any) -> List[Any]:
        """Parse raw payload into validated Pydantic models or domain dictionaries."""
        raise NotImplementedError

    @abstractmethod
    def get_fallback(self, **kwargs: Any) -> List[Any]:
        """Generate schema-conforming fallback data using FallbackTemplateEngine with is_estimated = True."""
        raise NotImplementedError

    async def run(self, **kwargs: Any) -> List[Any]:
        """
        Executes ingestion lifecycle:
        1. Check circuit breaker. If open, return get_fallback().
        2. Attempt fetch_data().
        3. If successful, parse_and_validate() and reset failure counters.
        4. If error occurs, increment failure counter, trip circuit breaker if threshold reached,
           and gracefully return get_fallback().
        """
        self.last_run = datetime.now(timezone.utc)

        if self._check_circuit_breaker():
            return self.get_fallback(**kwargs)

        try:
            raw_data = await self.fetch_data(**kwargs)
            parsed_results = self.parse_and_validate(raw_data)

            # Mark healthy on success
            self.is_healthy = True
            self.consecutive_failures = 0
            self.circuit_breaker_open = False
            self.circuit_breaker_tripped_at = None
            self.last_error = None
            return parsed_results

        except Exception as exc:
            self.consecutive_failures += 1
            self.is_healthy = False
            self.last_error = f"{type(exc).__name__}: {str(exc)}"

            if self.consecutive_failures >= self.max_failures_before_circuit_break:
                self.circuit_breaker_open = True
                self.circuit_breaker_tripped_at = datetime.now(timezone.utc)
                logger.error(
                    "Circuit breaker TRIPPED for %s after %d consecutive failures: %s",
                    self.stream_id,
                    self.consecutive_failures,
                    self.last_error,
                )
            else:
                logger.warning(
                    "Ingestion error on %s (attempt %d/%d): %s. Activating graceful fallback.",
                    self.stream_id,
                    self.consecutive_failures,
                    self.max_failures_before_circuit_break,
                    self.last_error,
                )

            return self.get_fallback(**kwargs)
