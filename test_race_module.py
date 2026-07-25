"""
test_race_module.py
White-box unit test suite for car.py and race_engine.py.

Each test is labelled with its Test Case ID (TC01-TC16) from the
SQAT assignment's test design table (equivalence partitioning,
boundary value analysis, and state-transition testing).
Run with: pytest -v
"""

import pytest
from car import Car, InvalidRaceStateError
from payout_service import PayoutError, PayoutService
from race_engine import RaceEngine


# ---------- helpers ----------

def new_car(car_id="C1", driver="Driver A", laps=3):
    return Car(car_id, driver, laps)


# ---------- TC01-TC06: complete_lap() ----------

def test_tc01_valid_lap_updates_time_and_lap_count():
    car = new_car()
    result = car.complete_lap(90000, 95)
    assert car.race_time_ms == 90000
    assert car.current_lap == 1
    assert result == "OK"


def test_tc02_zero_lap_time_rejected():
    car = new_car()
    with pytest.raises(ValueError):
        car.complete_lap(0, 95)


def test_tc03_negative_lap_time_rejected():
    car = new_car()
    with pytest.raises(ValueError):
        car.complete_lap(-500, 95)


def test_tc04_tyre_temp_at_threshold_triggers_alert():
    car = new_car()
    result = car.complete_lap(90000, 120)
    assert result == "TYRE_ALERT_PIT_REQUIRED"


def test_tc05_tyre_temp_just_below_threshold_is_safe():
    car = new_car()
    result = car.complete_lap(90000, 119)
    assert result == "OK"


def test_tc06_final_lap_marks_car_finished():
    car = new_car(laps=3)
    car.complete_lap(90000, 95)
    car.complete_lap(90000, 95)
    car.complete_lap(90000, 95)
    assert car.finished is True


# ---------- TC07-TC08: invalid state transitions on complete_lap ----------

def test_tc07_cannot_log_lap_after_finished():
    car = new_car(laps=1)
    car.complete_lap(90000, 95)  # finishes here
    with pytest.raises(InvalidRaceStateError):
        car.complete_lap(90000, 95)


def test_tc08_cannot_log_lap_while_in_pit():
    car = new_car()
    car.enter_pit()
    with pytest.raises(InvalidRaceStateError):
        car.complete_lap(90000, 95)


# ---------- TC09-TC12: pit stop behavior ----------

def test_tc09_pit_time_added_to_total_not_race_time():
    car = new_car()
    car.complete_lap(90000, 95)
    car.enter_pit()
    car.exit_pit(25000)
    assert car.pit_stop_time_ms == 25000
    assert car.race_time_ms == 90000


def test_tc10_exit_pit_resets_tyre_temperature():
    car = new_car()
    car.complete_lap(90000, 118)
    car.enter_pit()
    car.exit_pit(25000)
    assert car.tyre_temp_c == 90


def test_tc11_cannot_exit_pit_when_not_in_pit():
    car = new_car()
    with pytest.raises(InvalidRaceStateError):
        car.exit_pit(1000)


def test_tc12_negative_pit_duration_rejected():
    car = new_car()
    car.enter_pit()
    with pytest.raises(ValueError):
        car.exit_pit(-100)


# ---------- TC13-TC16: RaceEngine.get_winner() ----------

def test_tc13_winner_is_lowest_total_time_among_finished_cars():
    car_a = new_car("A", "Driver A", laps=1)
    car_b = new_car("B", "Driver B", laps=1)
    car_a.complete_lap(80000, 95)   # total 80000
    car_b.complete_lap(90000, 95)   # total 90000

    winner = RaceEngine([car_a, car_b]).get_winner()
    assert winner.car_id == "A"


def test_tc14_unfinished_cars_excluded_even_if_faster():
    car_a = new_car("A", "Driver A", laps=1)
    car_b = new_car("B", "Driver B", laps=2)
    car_a.complete_lap(80000, 95)   # finished, total 80000
    car_b.complete_lap(10000, 95)   # faster so far but NOT finished (needs 2 laps)

    winner = RaceEngine([car_a, car_b]).get_winner()
    assert winner.car_id == "A"


def test_tc15_no_winner_when_no_car_has_finished():
    car_a = new_car("A", "Driver A", laps=3)
    car_b = new_car("B", "Driver B", laps=3)
    car_a.complete_lap(80000, 95)
    car_b.complete_lap(85000, 95)

    winner = RaceEngine([car_a, car_b]).get_winner()
    assert winner is None


# ---------- TC17-TC20: record_speed() (FR2) ----------

def test_tc17_speed_below_minimum_rejected():
    car = new_car()
    with pytest.raises(ValueError):
        car.record_speed(249)


def test_tc18_speed_at_minimum_boundary_accepted():
    car = new_car()
    car.record_speed(250)
    assert car.last_speed_kmph == 250


def test_tc19_speed_at_maximum_boundary_accepted():
    car = new_car()
    car.record_speed(350)
    assert car.last_speed_kmph == 350


def test_tc20_speed_above_maximum_rejected():
    car = new_car()
    with pytest.raises(ValueError):
        car.record_speed(351)


def test_tc21_cannot_payout_when_no_winner():
    service = PayoutService()
    with pytest.raises(PayoutError):
        service.trigger_payout(None)


def test_tc22_payout_returns_correct_record_for_winner():
    service = PayoutService()
    winner = new_car("A", "Team Alpha", laps=1)
    winner.complete_lap(80000, 95)
    record = service.trigger_payout(winner)
    assert record["car_id"] == "A"
    assert record["driver_name"] == "Team Alpha"
    assert record["status"] == "PAID"
    assert record["amount"] > 0


def test_tc23_cannot_payout_same_car_twice():
    service = PayoutService()
    winner = new_car("A", "Team Alpha", laps=1)
    winner.complete_lap(80000, 95)
    service.trigger_payout(winner)
    with pytest.raises(PayoutError):
        service.trigger_payout(winner)


def test_tc16_pit_stop_can_flip_the_race_outcome():
    car_a = new_car("A", "Driver A", laps=1)  # faster laps, but pits
    car_b = new_car("B", "Driver B", laps=1)  # slower laps, no pit stop

    car_a.enter_pit()
    car_a.exit_pit(40000)
    car_a.complete_lap(70000, 95)   # total = 40000 + 70000 = 110000

    car_b.complete_lap(95000, 95)   # total = 95000, no pit stop

    winner = RaceEngine([car_a, car_b]).get_winner()
    assert winner.car_id == "B"
