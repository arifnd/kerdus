from __future__ import annotations

from . import desec, dokploy, porkbun
from .base import LocalTool

__all__ = ["build_local_tools"]


def build_local_tools(
    porkbun_enabled: bool = True,
    desec_enabled: bool = True,
    dokploy_enabled: bool = True,
) -> list[LocalTool]:
    tools: list[LocalTool] = []

    if porkbun_enabled:
        tools.extend(porkbun.build_porkbun_tools())

    if desec_enabled:
        tools.extend(desec.build_desec_tools())

    if dokploy_enabled:
        tools.extend(dokploy.build_dokploy_tools())

    return tools
