from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.scheduler.jobs import StateTracker, run_uptime_job
from app.scheduler.persistence import load_schedules, save_schedules
from app.scheduler.scheduler import SchedulerService


class TestStateTracker:
    def test_initial_get_is_none(self) -> None:
        t = StateTracker()
        assert t.get("x") is None

    def test_set_and_get(self) -> None:
        t = StateTracker()
        t.set("x", "up")
        assert t.get("x") == "up"


class TestRunUptimeJob:
    async def test_first_check_emits_event(self, monkeypatch) -> None:
        tracker = StateTracker()

        async def fake_check(url: str) -> dict:
            return {"url": url, "up": True, "status_code": 200, "latency_ms": 10}

        monkeypatch.setattr("app.scheduler.jobs.check_uptime", fake_check)
        job = {"id": "j", "type": "uptime", "url": "https://a.com", "interval_seconds": 60, "enabled": True}
        event = await run_uptime_job(job, tracker)
        assert event is not None
        assert event.kind == "up"
        assert event.job_id == "j"

    async def test_steady_state_emits_nothing(self, monkeypatch) -> None:
        tracker = StateTracker()
        tracker.set("j", "up")

        async def fake_check(url: str) -> dict:
            return {"url": url, "up": True, "status_code": 200, "latency_ms": 10}

        monkeypatch.setattr("app.scheduler.jobs.check_uptime", fake_check)
        job = {"id": "j", "type": "uptime", "url": "https://a.com", "interval_seconds": 60, "enabled": True}
        assert await run_uptime_job(job, tracker) is None

    async def test_state_change_down_to_up_emits(self, monkeypatch) -> None:
        tracker = StateTracker()
        tracker.set("j", "down")

        async def fake_check(url: str) -> dict:
            return {"url": url, "up": True, "status_code": 200, "latency_ms": 10}

        monkeypatch.setattr("app.scheduler.jobs.check_uptime", fake_check)
        job = {"id": "j", "type": "uptime", "url": "https://a.com", "interval_seconds": 60, "enabled": True}
        event = await run_uptime_job(job, tracker)
        assert event is not None
        assert event.kind == "up"


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "schedules.json"
        jobs = [{"id": "a", "type": "uptime", "url": "https://a.com", "interval_seconds": 300, "enabled": True}]
        save_schedules(path, jobs)
        loaded = load_schedules(path)
        assert loaded == jobs

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        assert load_schedules(tmp_path / "nope.json") == []

    def test_load_corrupt_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{ not json", encoding="utf-8")
        assert load_schedules(path) == []

    def test_save_is_atomic(self, tmp_path: Path) -> None:
        path = tmp_path / "sched.json"
        save_schedules(path, [{"id": "a", "enabled": True}])
        save_schedules(path, [{"id": "b", "enabled": False}])
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["jobs"][0]["id"] == "b"


@pytest.fixture()
def scheduler(tmp_path):
    s = SchedulerService(state_path=tmp_path / "schedules.json")
    s.load_state()
    return s


class TestSchedulerService:
    async def test_create_persists_and_restores(self, scheduler: SchedulerService, tmp_path: Path) -> None:
        res = await scheduler.create("site-1", "https://example.com", 300)
        assert res["success"] is True

        new_svc = SchedulerService(state_path=tmp_path / "schedules.json")
        new_svc.load_state()
        jobs = await new_svc.list()
        assert jobs == [
            {
                "id": "site-1",
                "url": "https://example.com",
                "interval_seconds": 300,
                "enabled": True,
            }
        ]

    async def test_duplicate_create_raises(self, scheduler: SchedulerService) -> None:
        await scheduler.create("dup", "https://a.com", 60)
        with pytest.raises(ValueError):
            await scheduler.create("dup", "https://a.com", 60)

    async def test_pause_removes_schedule(self, scheduler: SchedulerService) -> None:
        await scheduler.create("p", "https://a.com", 60)
        await scheduler.pause("p")
        assert scheduler._scheduler.get_job("p") is None
        jobs = await scheduler.list()
        assert jobs[0]["enabled"] is False

    async def test_resume_reschedules(self, scheduler: SchedulerService) -> None:
        await scheduler.create("r", "https://a.com", 60)
        await scheduler.pause("r")
        await scheduler.resume("r")
        assert scheduler._scheduler.get_job("r") is not None
        jobs = await scheduler.list()
        assert jobs[0]["enabled"] is True

    async def test_remove(self, scheduler: SchedulerService) -> None:
        await scheduler.create("rm", "https://a.com", 60)
        await scheduler.remove("rm")
        assert await scheduler.list() == []

    async def test_start_and_shutdown(self, scheduler: SchedulerService) -> None:
        await scheduler.create("s", "https://a.com", 60)
        scheduler.start()
        assert scheduler._scheduler.running
        scheduler.shutdown()
        await asyncio.sleep(0)
        assert not scheduler._scheduler.running

    async def test_status_handler_receives_event(self, scheduler: SchedulerService, monkeypatch) -> None:
        events = []

        async def handler(event) -> None:
            events.append(event)

        scheduler.add_status_handler(handler)

        async def fake_check(url: str) -> dict:
            return {"url": url, "up": False, "status_code": None, "latency_ms": 5, "error": "x"}

        monkeypatch.setattr("app.scheduler.jobs.check_uptime", fake_check)
        job = {"id": "h", "type": "uptime", "url": "https://a.com", "interval_seconds": 60, "enabled": True}
        scheduler._jobs["h"] = job
        await scheduler._run_job(job)
        assert len(events) == 1
        assert events[0].kind == "down"

        await scheduler._run_job(job)
        assert len(events) == 1
