"""Plugin loader for the gateway."""

from __future__ import annotations

import importlib
import os
from typing import List, Type

from fastapi import FastAPI

from .base import GatewayPlugin


DEFAULT_PLUGIN_SPECS = "gateway.plugins.verify:VerifyWithCAPlugin,gateway.plugins.purpose:PurposeBindingPlugin"


def _import_from_spec(spec: str) -> type:
    if ":" not in spec:
        raise ValueError(f"invalid plugin spec '{spec}' (expected module:Class)")
    mod_name, attr = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, attr)
    if not isinstance(cls, type):
        raise ValueError(f"plugin '{spec}' is not a class")
    return cls


def load_plugins(app: FastAPI) -> List[GatewayPlugin]:
    """Load plugins declared by env var.

    Configure via:
      GATEWAY_PLUGINS=module:Class,module:Class

    Each plugin class must accept `app` as its single constructor argument.
    """

    raw = os.getenv("GATEWAY_PLUGINS", DEFAULT_PLUGIN_SPECS)
    specs = [s.strip() for s in raw.split(",") if s.strip()]
    plugins: List[GatewayPlugin] = []
    for spec in specs:
        cls: Type = _import_from_spec(spec)
        plugins.append(cls(app))  # type: ignore[call-arg]
    return plugins
