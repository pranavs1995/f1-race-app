"""
demo.py
Runs the race flow through the live Flask backend API so the same routes
used by the web UI are exercised end-to-end.
"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"


def python_with_flask() -> str:
    if importlib.util.find_spec("flask"):
        return sys.executable

    venv_python = Path(__file__).resolve().parent / "venv" / "bin" / "python3"
    if venv_python.exists():
        try:
            result = subprocess.run(
                [str(venv_python), "-c", "import importlib.util; print(importlib.util.find_spec('flask') is not None)"],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip() == "True":
                return str(venv_python)
        except subprocess.SubprocessError:
            pass

    raise RuntimeError(
        "Flask is not installed in the current Python interpreter. "
        "Activate the project's virtual environment or install Flask before running demo.py."
    )


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def ensure_server() -> None:
    global BASE_URL

    def is_our_app(url: str) -> bool:
        try:
            with urllib.request.urlopen(f"{url}/api/state", timeout=2) as response:
                if response.status != 200:
                    return False
                data = json.loads(response.read().decode("utf-8"))
                return isinstance(data, dict) and "cars" in data and "winner" in data
        except Exception:
            return False

    if is_our_app(BASE_URL):
        return

    port = find_free_port()
    BASE_URL = f"http://127.0.0.1:{port}"
    python_exec = python_with_flask()
    print(f"Starting Flask backend on {BASE_URL} using {python_exec}...")
    env = dict(**os.environ, RACE_APP_PORT=str(port))
    process = subprocess.Popen(
        [python_exec, "app.py"],
        cwd=str(Path(__file__).resolve().parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(60):
        if is_our_app(BASE_URL):
            webbrowser.open(BASE_URL)
            return BASE_URL
        if process.poll() is not None:
            raise RuntimeError("Flask backend process exited before startup.")
        time.sleep(0.2)

    raise RuntimeError("The Flask backend did not start in time.")


def print_state(data: dict, label: str) -> None:
    print(f"\n[{label}]")
    for car in data["cars"]:
        print(
            f"  {car['driver_name']}: lap {car['current_lap']}/{car['total_laps']} | "
            f"race={car['race_time_ms']} ms | pit={car['pit_stop_time_ms']} ms | "
            f"total={car['total_time_ms']} ms | tyre={car['tyre_temp_c']}C | "
            f"finished={car['finished']}"
        )
    winner = data.get("winner")
    if winner:
        print(f"  winner: {winner['driver_name']} ({winner['id']})")
    else:
        print("  winner: none yet")


def call_api(method: str, path: str, payload=None) -> dict:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if response.status >= 400:
                raise RuntimeError(data.get("error", f"Request failed ({response.status} )"))
            return data
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8")
        data = json.loads(body_text) if body_text else {}
        raise RuntimeError(data.get("error", f"Request failed ({exc.code})")) from exc


def main() -> None:
    ui_url = ensure_server()

    print("=" * 70)
    print("FORMULA ONE RACE APPLICATION - API-driven demo")
    print("=" * 70)
    if ui_url:
        print(f"UI launched at: {ui_url}")

    call_api("POST", "/api/reset")
    print_state(call_api("GET", "/api/state"), "Initial state")

    print("\n-- Speed validation --")
    call_api("POST", "/api/cars/A/speed", {"speed_kmph": 312})
    print("  Team Alpha: speed accepted")
    try:
        call_api("POST", "/api/cars/B/speed", {"speed_kmph": 400})
    except RuntimeError as exc:
        print(f"  Team Beta: rejected speed -> {exc}")

    print("\n-- Lap 1 --")
    call_api("POST", "/api/cars/A/lap")
    call_api("POST", "/api/cars/B/lap")
    print_state(call_api("GET", "/api/state"), "After lap 1")

    print("\n-- Lap 2 with tyre alert --")
    call_api("POST", "/api/cars/A/lap")
    call_api("POST", "/api/cars/B/lap")
    print_state(call_api("GET", "/api/state"), "After lap 2")

    print("\n-- Pit stop for Team Alpha --")
    call_api("POST", "/api/cars/A/pit/enter")
    call_api("POST", "/api/cars/A/pit/exit", {"duration_ms": 24000})
    print_state(call_api("GET", "/api/state"), "After pit stop")

    print("\n-- Final lap --")
    call_api("POST", "/api/cars/A/lap")
    call_api("POST", "/api/cars/B/lap")
    final_state = call_api("GET", "/api/state")
    print_state(final_state, "Final state")

    print("\n" + "=" * 70)
    if final_state.get("winner"):
        winner = final_state["winner"]
        print(f"WINNER: {winner['driver_name']} ({winner['id']}) with total time {winner['total_time_ms']} ms")
    else:
        print("WINNER: none")
    print("=" * 70)
    print("\nThe browser UI should now show the same race events from the shared backend log.")


if __name__ == "__main__":
    main()
