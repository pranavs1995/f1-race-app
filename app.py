"""
app.py
Flask backend for the Formula One Race Application.

This is the single source of truth: it wraps car.py / race_engine.py
(the same classes covered by test_race_module.py) behind a small REST
API. index.html is a thin client that only renders state returned by
this server and calls these endpoints — it contains no race logic of
its own, so the UI and the tested backend can never drift apart.

Run with: python3 app.py
Then open: http://127.0.0.1:5000
"""

import os
import random
from flask import Flask, jsonify, request, send_from_directory

from car import Car, InvalidRaceStateError, TYRE_MAX_SAFE_TEMP_C
from payout_service import PayoutService
from race_engine import RaceEngine

app = Flask(__name__, static_folder=".")

TOTAL_LAPS = 3


def fresh_race():
    return {
        "A": Car("A", "Team Alpha", TOTAL_LAPS),
        "B": Car("B", "Team Beta", TOTAL_LAPS),
    }


cars = fresh_race()
activity_log = []
payout_service = PayoutService()


def append_log(message: str) -> None:
    activity_log.append(message)
    if len(activity_log) > 50:
        activity_log.pop(0)


def car_to_dict(car: Car) -> dict:
    average_lap_ms = car.race_time_ms // car.current_lap if car.current_lap else 0
    tyre_status = "TYRE_ALERT_PIT_REQUIRED" if car.tyre_temp_c >= TYRE_MAX_SAFE_TEMP_C else "OK"
    return {
        "id": car.car_id,
        "driver_name": car.driver_name,
        "current_lap": car.current_lap,
        "total_laps": car.total_laps,
        "laps_remaining": max(car.total_laps - car.current_lap, 0),
        "race_time_ms": car.race_time_ms,
        "pit_stop_time_ms": car.pit_stop_time_ms,
        "total_time_ms": car.total_time_ms(),
        "average_lap_time_ms": average_lap_ms,
        "tyre_temp_c": car.tyre_temp_c,
        "tyre_status": tyre_status,
        "last_speed_kmph": car.last_speed_kmph,
        "pit_stop_count": car.pit_stop_count,
        "in_pit": car.in_pit,
        "finished": car.finished,
    }


def state_response():
    engine = RaceEngine(list(cars.values()))
    winner = engine.get_winner()

    payout = None
    if winner is not None:
        if payout_service.has_been_paid(winner.car_id):
            payout = {"car_id": winner.car_id, "status": "PAID"}
        else:
            payout = payout_service.trigger_payout(winner)

    return jsonify({
        "cars": [car_to_dict(c) for c in cars.values()],
        "winner": car_to_dict(winner) if winner else None,
        "payout": payout,
        "log": activity_log,
    })


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/api/state")
def get_state():
    return state_response()


@app.post("/api/reset")
def reset_race():
    global cars, payout_service
    cars = fresh_race()
    payout_service = PayoutService()
    activity_log.clear()
    append_log("Race reset — 2 cars, 3 laps each.")
    return state_response()


@app.post("/api/cars/<car_id>/lap")
def complete_lap(car_id):
    car = cars.get(car_id)
    if car is None:
        return jsonify({"error": f"Unknown car_id '{car_id}'"}), 404

    # Simulated telemetry for this lap (a real system would read this
    # from track sensors); tyre temp drifts upward each lap.
    lap_time_ms = random.randint(85000, 95000)
    tyre_temp_c = car.tyre_temp_c + random.randint(6, 12)

    try:
        status = car.complete_lap(lap_time_ms, tyre_temp_c)
    except (InvalidRaceStateError, ValueError) as e:
        append_log(f"{car.driver_name}: rejected lap request — {e}")
        return jsonify({"error": str(e)}), 400

    append_log(f"{car.driver_name}: lap {car.current_lap}/{car.total_laps} complete — tyre check: {status}")
    resp = state_response()
    data = resp.get_json()
    data["tyre_status"] = status
    return jsonify(data)


@app.post("/api/cars/<car_id>/pit/enter")
def enter_pit(car_id):
    car = cars.get(car_id)
    if car is None:
        return jsonify({"error": f"Unknown car_id '{car_id}'"}), 404
    try:
        car.enter_pit()
    except InvalidRaceStateError as e:
        append_log(f"{car.driver_name}: rejected pit entry — {e}")
        return jsonify({"error": str(e)}), 400

    append_log(f"{car.driver_name}: entered pit lane")
    return state_response()


@app.post("/api/cars/<car_id>/pit/exit")
def exit_pit(car_id):
    car = cars.get(car_id)
    if car is None:
        return jsonify({"error": f"Unknown car_id '{car_id}'"}), 404
    duration_ms = int(request.json.get("duration_ms", 25000)) if request.is_json else 25000
    try:
        car.exit_pit(duration_ms)
    except (InvalidRaceStateError, ValueError) as e:
        append_log(f"{car.driver_name}: rejected pit exit — {e}")
        return jsonify({"error": str(e)}), 400

    append_log(f"{car.driver_name}: exited pit (+{duration_ms/1000:.1f}s), fresh tyres fitted")
    return state_response()


@app.post("/api/cars/<car_id>/speed")
def record_speed(car_id):
    car = cars.get(car_id)
    if car is None:
        return jsonify({"error": f"Unknown car_id '{car_id}'"}), 404
    if not request.is_json or "speed_kmph" not in request.json:
        return jsonify({"error": "speed_kmph is required"}), 400
    try:
        car.record_speed(float(request.json["speed_kmph"]))
    except ValueError as e:
        append_log(f"{car.driver_name}: rejected speed — {e}")
        return jsonify({"error": str(e)}), 400

    append_log(f"{car.driver_name}: recorded speed {float(request.json['speed_kmph']):.0f} kmph")
    return state_response()


if __name__ == "__main__":
    port = int(os.environ.get("RACE_APP_PORT", 5000))
    app.run(debug=True, port=port, use_reloader=False)
