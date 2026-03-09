from __future__ import annotations

import inspect
from typing import Any
from uuid import UUID, uuid4


class Saga:
    """Base class for all saga orchestrators.

    A saga encapsulates a multi-step transaction that may span Office Hero and an
    external back-office system.  Operational state (steps completed, idem keys,
    etc.) will eventually be persisted in ``saga_log``; the base class provides a
    small helper to enqueue events into the transactional outbox.
    """

    def __init__(
        self,
        tenant_id: UUID,
        outbox_repo: Any = None,
        saga_log_repo: Any = None,
    ):
        self.tenant_id = tenant_id
        self._outbox = outbox_repo
        self._saga_log = saga_log_repo

    async def enqueue_outbox_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        idem_key: UUID | None = None,
    ) -> dict[str, Any]:
        """Create an outbox event and persist it if a repository is supplied.

        The event dictionary mirrors the structure defined in the ADR: it contains
        ``tenant_id``, ``event_type``, ``payload`` and an ``idem_key`` that is
        used for idempotency when processing the outbox.  If ``idem_key`` is not
        provided a new ``UUID`` is generated.
        """
        if idem_key is None:
            idem_key = uuid4()
        event = {
            "tenant_id": self.tenant_id,
            "event_type": event_type,
            "payload": payload,
            "idem_key": idem_key,
        }

        if self._outbox is not None:
            # the repository may provide either ``insert`` or ``create``; each
            # could be async or sync.  We *do not* want to swallow unexpected
            # errors, hence the more explicit handling below.
            try:
                await self._outbox.insert(event)
            except TypeError:
                # returned a non-awaitable (sync implementation)
                self._outbox.insert(event)
            except AttributeError:
                # ``insert`` doesn't exist; try ``create`` instead.
                # Since we already know ``insert`` is missing, AttributeError here
                # means the attribute lookup failed.  Replace the prior blanket
                # suppression with conditional logic so that real exceptions
                # propagate.
                if hasattr(self._outbox, "create"):
                    result = self._outbox.create(event)
                    if inspect.isawaitable(result):
                        await result  # type: ignore
                else:
                    # neither method is available; propagate the original
                    # AttributeError so callers can notice misconfiguration.
                    raise
        return event
