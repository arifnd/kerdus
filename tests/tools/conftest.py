from __future__ import annotations

import pytest

from app.tools import build_local_tools


@pytest.fixture()
def tools():
    return build_local_tools(porkbun_enabled=True, desec_enabled=True, dokploy_enabled=True)
