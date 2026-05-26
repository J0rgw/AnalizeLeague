"""
Unit tests for the Data Dragon-backed champion-name resolver.

The autouse `_no_network_ddragon` fixture in conftest.py stubs the network
call, so these tests control behaviour by re-patching _fetch_champion_json.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.digest import champions as champions_mod
from app.digest.champions import resolve_champion_name


def _fake_ddragon_payload() -> dict[str, Any]:
    return {
        "type": "champion",
        "format": "standAloneComplex",
        "version": "14.10.1",
        "data": {
            "Yasuo": {"key": "157", "id": "Yasuo", "name": "Yasuo"},
            "Zed": {"key": "238", "id": "Zed", "name": "Zed"},
        },
    }


def test_resolves_known_id_to_canonical_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(champions_mod, "_fetch_champion_json", lambda _v: _fake_ddragon_payload())
    assert resolve_champion_name(157, patch="14.10") == "Yasuo"
    assert resolve_champion_name("238", patch="14.10") == "Zed"


def test_unknown_id_degrades_to_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(champions_mod, "_fetch_champion_json", lambda _v: _fake_ddragon_payload())
    assert resolve_champion_name(99_999, patch="14.10") == "99999"


def test_no_network_no_cache_degrades_gracefully() -> None:
    # Autouse fixture already sets _fetch_champion_json to return None.
    assert resolve_champion_name(157, patch="14.10") == "157"
    # And: should not raise on weird input.
    assert resolve_champion_name("", patch="14.10") == ""
    assert resolve_champion_name(None, patch="14.10") == ""  # type: ignore[arg-type]
    assert resolve_champion_name("not-a-number", patch="14.10") == "not-a-number"


def test_in_process_cache_avoids_repeat_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def counting_fetch(version: str) -> dict[str, Any] | None:
        calls.append(version)
        return _fake_ddragon_payload()

    monkeypatch.setattr(champions_mod, "_fetch_champion_json", counting_fetch)
    resolve_champion_name(157, patch="14.10")
    resolve_champion_name(238, patch="14.10")
    resolve_champion_name(99_999, patch="14.10")
    assert calls == ["14.10.1"]  # only one network call across three lookups


def test_version_for_patch_falls_back_for_garbage_input() -> None:
    assert champions_mod._version_for_patch(None) == champions_mod._DEFAULT_VERSION
    assert champions_mod._version_for_patch("") == champions_mod._DEFAULT_VERSION
    assert champions_mod._version_for_patch("garbage") == champions_mod._DEFAULT_VERSION
    assert champions_mod._version_for_patch("14.10") == "14.10.1"
    assert champions_mod._version_for_patch("14.10.123.4567") == "14.10.1"
