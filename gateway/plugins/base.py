from __future__ import annotations

"""Gateway plugin interfaces.

Week 5/6 backlog: Gateway pluginization.

The gateway runs a configurable pipeline of validation plugins.
Each plugin may:
- Read request headers/path
- Mutate the GatewayContext
- Return a Response to short-circuit the request
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

from fastapi import Request
from fastapi.responses import Response


@dataclass
class GatewayContext:
    correlation_id: str
    coupon: Optional[str] = None
    claims: Dict[str, Any] = field(default_factory=dict)


class GatewayPlugin(Protocol):
    """A validation plugin.

    If `process()` returns a Response, the gateway returns it immediately.
    Otherwise the next plugin runs.
    """

    async def process(self, request: Request, ctx: GatewayContext) -> Optional[Response]:
        ...
