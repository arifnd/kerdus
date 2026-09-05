from __future__ import annotations

from app.tools import build_local_tools
from app.tools.desec import DeSecAPIError
from app.tools.dokploy import DokployAPIError
from app.tools.porkbun import PorkbunAPIError


class TestLocalToolsRegistry:
    def test_disabled_returns_empty(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=False, dokploy_enabled=False)
        assert tools == []

    def test_only_porkbun(self) -> None:
        tools = build_local_tools(porkbun_enabled=True, desec_enabled=False, dokploy_enabled=False)
        names = {t.name for t in tools}
        assert names
        assert all(n.startswith("porkbun_") for n in names)

    def test_only_desec(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=True, dokploy_enabled=False)
        names = {t.name for t in tools}
        assert names
        assert all(n.startswith("desec_") for n in names)

    def test_only_dokploy(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=False, dokploy_enabled=True)
        names = {t.name for t in tools}
        assert names
        assert all(n.startswith("dokploy_") for n in names)


class TestAPIErrors:
    def test_porkbun_error_attributes(self) -> None:
        exc = PorkbunAPIError(status="ERROR", message="not found")
        assert exc.status == "ERROR"
        assert exc.message == "not found"
        assert "not found" in str(exc)

    def test_desec_error_attributes(self) -> None:
        exc = DeSecAPIError(status=404, message="not found")
        assert exc.status == 404
        assert exc.message == "not found"
        assert "404" in str(exc)

    def test_dokploy_error_attributes(self) -> None:
        exc = DokployAPIError(status=403, message="forbidden")
        assert exc.status == 403
        assert exc.message == "forbidden"
        assert "403" in str(exc)