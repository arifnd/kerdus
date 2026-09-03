from __future__ import annotations

import pytest

from app.tools import build_local_tools
from app.tools.memory_scheduler import MemorySchedulerService
from app.tools.scheduler_tools import InputError, _validate_id, _validate_interval, _validate_url


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


@pytest.fixture()
def scheduler():
    return MemorySchedulerService()


@pytest.fixture()
def tools(scheduler):
    return build_local_tools(scheduler)


class TestValidateId:
    def test_valid(self) -> None:
        assert _validate_id("my-site") == "my-site"
        assert _validate_id("site_123") == "site_123"

    def test_empty(self) -> None:
        with pytest.raises(InputError):
            _validate_id("")

    def test_special_chars(self) -> None:
        with pytest.raises(InputError):
            _validate_id("my site")
        with pytest.raises(InputError):
            _validate_id("my.site")


class TestValidateUrl:
    def test_http(self) -> None:
        assert _validate_url("http://example.com") == "http://example.com"

    def test_https(self) -> None:
        assert _validate_url("https://example.com/health") == "https://example.com/health"

    def test_no_scheme(self) -> None:
        with pytest.raises(InputError):
            _validate_url("example.com")

    def test_ftp(self) -> None:
        with pytest.raises(InputError):
            _validate_url("ftp://example.com")


class TestValidateInterval:
    def test_valid(self) -> None:
        assert _validate_interval(30) == 30
        assert _validate_interval(86400) == 86400

    def test_too_small(self) -> None:
        with pytest.raises(InputError):
            _validate_interval(10)

    def test_too_large(self) -> None:
        with pytest.raises(InputError):
            _validate_interval(90000)

    def test_not_int(self) -> None:
        with pytest.raises(InputError):
            _validate_interval("60")  # type: ignore[arg-type]


class TestCheckUptime:
    async def test_check_uptime_returns_result(self) -> None:
        from app.tools.uptime import check_uptime

        result = await check_uptime("https://httpbin.org/get")
        assert result["url"] == "https://httpbin.org/get"
        assert "up" in result
        assert "latency_ms" in result

    async def test_check_uptime_bad_url(self) -> None:
        from app.tools.uptime import check_uptime

        result = await check_uptime("http://192.0.2.1:1")
        assert result["up"] is False
        assert "error" in result


class TestMemorySchedulerService:
    async def test_create_and_list(self, scheduler: MemorySchedulerService) -> None:
        res = await scheduler.create("site-1", "https://example.com", 300)
        assert res["success"] is True
        jobs = await scheduler.list()
        assert len(jobs) == 1
        assert jobs[0]["id"] == "site-1"
        assert jobs[0]["enabled"] is True

    async def test_duplicate_create_raises(self, scheduler: MemorySchedulerService) -> None:
        await scheduler.create("dup", "https://a.com", 60)
        with pytest.raises(ValueError):
            await scheduler.create("dup", "https://a.com", 60)

    async def test_pause_and_resume(self, scheduler: MemorySchedulerService) -> None:
        await scheduler.create("site-2", "https://a.com", 120)
        await scheduler.pause("site-2")
        jobs = await scheduler.list()
        assert jobs[0]["enabled"] is False
        await scheduler.resume("site-2")
        jobs = await scheduler.list()
        assert jobs[0]["enabled"] is True

    async def test_remove(self, scheduler: MemorySchedulerService) -> None:
        await scheduler.create("del-me", "https://a.com", 60)
        await scheduler.remove("del-me")
        assert await scheduler.list() == []

    async def test_pause_nonexistent_raises(self, scheduler: MemorySchedulerService) -> None:
        with pytest.raises(ValueError):
            await scheduler.pause("nope")


class TestLocalToolsRegistry:
    def test_registry_has_all_expected_tools(self, tools) -> None:
        names = {t.name for t in tools}
        expected = {
            "check_uptime",
            "create_uptime_check",
            "list_scheduled_checks",
            "remove_scheduled_check",
            "pause_scheduled_check",
            "resume_scheduled_check",
        }
        assert expected == names

    async def test_create_uptime_check_via_registry(self, tools, scheduler: MemorySchedulerService) -> None:
        create = _get_tool(tools, "create_uptime_check")
        res = await create.func(id="x", url="https://a.com", interval_seconds=60)
        assert res["success"] is True
        jobs = await scheduler.list()
        assert len(jobs) == 1

    async def test_list_scheduled_checks_via_registry(self, tools, scheduler: MemorySchedulerService) -> None:
        list_tool = _get_tool(tools, "list_scheduled_checks")
        result = await list_tool.func()
        assert result == []

    async def test_create_id_validation_via_registry(self, tools) -> None:
        create = _get_tool(tools, "create_uptime_check")
        with pytest.raises(InputError):
            await create.func(id="bad id", url="https://a.com", interval_seconds=60)