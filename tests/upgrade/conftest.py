"""Two-phase upgrade harness for Car Keeper.

Phase 1 boots the oldest supported Home Assistant (``ci/oldest-ha.env``) with the
oldest supported Home Keeper (``const.HOME_KEEPER_MIN_VERSION``) on a temporary copy
of the seeded config dir, and writes data through the services. Phase 2 stops it and
boots the newer Home Assistant (``HA_TAG``, default ``stable``) with the newer Home
Keeper (``HK_NEW_DIR``) on the same dir. The tests then check what stayed.

A user who updates Home Assistant and Home Keeper keeps the same ``.storage``. This
tier proves that Car Keeper loads that storage again, keeps every record, and gets
its tab back with no repair issue.

Run it with::

    HOME_KEEPER_REF=v0.35.0 bash ci/fetch-home-keeper.sh   # copy to HK_OLD_DIR
    HOME_KEEPER_REF=main bash ci/fetch-home-keeper.sh      # copy to HK_NEW_DIR
    HK_OLD_DIR=... HK_NEW_DIR=... python -m pytest tests/upgrade -v

``ci/test-upgrade.sh`` does all 3 steps.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import requests
from websockets.sync.client import connect

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
COMPOSE = HERE / "docker-compose.yml"
SEED = ROOT / "tests" / "integration" / "ha_config"
PROJECT = "ck-upgrade"
HA_PORT = os.environ.get("HA_PORT", "8124")
HA_URL = f"http://localhost:{HA_PORT}"
BOOT_TIMEOUT = 240


def _env_file() -> dict[str, str]:
    out = {}
    for line in (ROOT / "ci" / "oldest-ha.env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


OLD_HA_TAG = os.environ.get("UPGRADE_OLD_HA_TAG", _env_file()["OLDEST_HA"])
NEW_HA_TAG = os.environ.get("HA_TAG", "stable")


def _compose(config: Path, ha_tag: str, hk_dir: str, *args: str) -> None:
    env = {
        **os.environ,
        "HA_TAG": ha_tag,
        "HA_CONFIG": str(config),
        "HK_DIR": hk_dir,
        "HA_PORT": HA_PORT,
    }
    subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args],
        env=env,
        check=True,
        capture_output=True,
    )


class Client:
    """REST and websocket access to the Home Assistant under test."""

    def __init__(self) -> None:
        self.token = ""

    def wait(self) -> None:
        deadline = time.monotonic() + BOOT_TIMEOUT
        while time.monotonic() < deadline:
            try:
                code = requests.get(f"{HA_URL}/api/", timeout=5).status_code
                if code in (200, 401):
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        else:
            raise TimeoutError("Home Assistant did not start")
        self.token = _token()
        deadline = time.monotonic() + BOOT_TIMEOUT
        while time.monotonic() < deadline:
            state = self.get("/api/config").get("state")
            loaded = {e["domain"]: e["state"] for e in self.entries()}
            if state == "RUNNING" and loaded.get("car_keeper") == "loaded":
                return
            time.sleep(2)
        raise TimeoutError(f"Car Keeper did not load: {self.entries()}")

    def get(self, path: str) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"}
        return requests.get(f"{HA_URL}{path}", headers=headers, timeout=30).json()

    def entries(self) -> list[dict[str, Any]]:
        return list(self.get("/api/config/config_entries/entry"))

    def call(self, service: str, data: dict[str, Any] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"}
        url = f"{HA_URL}/api/services/car_keeper/{service}?return_response"
        r = requests.post(url, headers=headers, json=data or {}, timeout=60)
        assert r.status_code == 200, (service, r.status_code, r.text)
        return r.json().get("service_response")

    def ws(self, command: str) -> Any:
        with connect(f"ws://localhost:{HA_PORT}/api/websocket") as sock:
            sock.recv(timeout=10)
            sock.send(json.dumps({"type": "auth", "access_token": self.token}))
            sock.recv(timeout=10)
            sock.send(json.dumps({"id": 1, "type": command}))
            reply = json.loads(sock.recv(timeout=30))
        assert reply.get("success"), reply
        return reply["result"]


def _token() -> str:
    """Make the onboarding user, or log in when onboarding is done."""
    client = f"{HA_URL}/"
    r = requests.post(
        f"{HA_URL}/api/onboarding/users",
        json={
            "client_id": client,
            "name": "Test",
            "username": "test",
            "password": "testtest1",
            "language": "en",
        },
        timeout=10,
    )
    if r.status_code == 200:
        code = r.json()["auth_code"]
    else:
        flow = requests.post(
            f"{HA_URL}/auth/login_flow",
            json={
                "client_id": client,
                "handler": ["homeassistant", None],
                "redirect_uri": client,
            },
            timeout=10,
        ).json()["flow_id"]
        code = requests.post(
            f"{HA_URL}/auth/login_flow/{flow}",
            json={"username": "test", "password": "testtest1", "client_id": client},
            timeout=10,
        ).json()["result"]
    tokens = requests.post(
        f"{HA_URL}/auth/token",
        data={"grant_type": "authorization_code", "code": code, "client_id": client},
        timeout=10,
    )
    tokens.raise_for_status()
    return str(tokens.json()["access_token"])


@pytest.fixture(scope="session")
def upgraded() -> Iterator[dict[str, Any]]:
    """Run both phases. Yield the client and what phase 1 wrote."""
    old_hk = os.environ.get("HK_OLD_DIR")
    new_hk = os.environ.get("HK_NEW_DIR")
    if not old_hk or not new_hk:
        pytest.fail("set HK_OLD_DIR and HK_NEW_DIR, or run ci/test-upgrade.sh")
    config = Path(tempfile.mkdtemp(prefix="ck-upgrade-"))
    shutil.copytree(SEED, config, dirs_exist_ok=True, ignore=_runtime_files)
    client = Client()
    try:
        _compose(config, OLD_HA_TAG, old_hk, "up", "-d")
        client.wait()
        written = client.call("set_settings", {"unit": "mi"})
        car = client.call(
            "add_car",
            {"name": "Upgrade car", "odometer": 12000, "starter_jobs": ["engine_oil"]},
        )["car"]
        items = client.call("list_items", {"car_id": car["id"]})["items"]
        client.call(
            "log_service",
            {"car_id": car["id"], "items": [items[0]["id"]], "reading": 12100},
        )
        before = client.ws("car_keeper/get_state")
        _compose(config, OLD_HA_TAG, old_hk, "stop")
        _compose(config, NEW_HA_TAG, new_hk, "up", "-d", "--force-recreate")
        client.wait()
        yield {"client": client, "before": before, "written": written}
    finally:
        _compose(config, NEW_HA_TAG, new_hk, "down", "-v")
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{config}:/config",
                "--entrypoint",
                "/bin/sh",
                f"ghcr.io/home-assistant/home-assistant:{NEW_HA_TAG}",
                "-c",
                "rm -rf /config/* /config/.[!.]* /config/..?*",
            ],
            check=False,
            capture_output=True,
        )
        shutil.rmtree(config, ignore_errors=True)


def _runtime_files(directory: str, names: list[str]) -> set[str]:
    """The files of a local run that the copy must not take."""
    path = Path(directory)
    if path.name == ".storage":
        return {n for n in names if n != "core.config_entries"}
    return {n for n in names if n in {".HA_VERSION", "home-assistant.log", "deps"}}
