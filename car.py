"""
car.py
Core domain object for the Formula One Race Application.

Represents a single participant car and its race state:
lap progress, race time, pit-stop time, and tyre temperature.
"""

TYRE_MAX_SAFE_TEMP_C = 120  # threshold above which a tyre blast is a risk
TYRE_NOMINAL_TEMP_C = 90    # temperature a tyre starts at / resets to after a pit stop
MIN_VALID_SPEED_KMPH = 250  # realistic F1 speed range per problem statement
MAX_VALID_SPEED_KMPH = 350


class InvalidRaceStateError(Exception):
    """Raised when a race operation is attempted in an invalid state."""
    pass


class Car:
    def __init__(self, car_id: str, driver_name: str, total_laps: int):
        if total_laps <= 0:
            raise ValueError("total_laps must be positive")

        self.car_id = car_id
        self.driver_name = driver_name
        self.total_laps = total_laps

        self.current_lap = 0
        self.race_time_ms = 0        # time spent actually racing
        self.pit_stop_time_ms = 0    # time spent in the pit lane
        self.tyre_temp_c = TYRE_NOMINAL_TEMP_C
        self.in_pit = False
        self.finished = False
        self.last_speed_kmph = None
        self.pit_stop_count = 0

    def complete_lap(self, lap_time_ms: int, tyre_temp_at_lap_end_c: float) -> str:
        """Log completion of one lap. Returns 'OK' or 'TYRE_ALERT_PIT_REQUIRED'."""
        if self.finished:
            raise InvalidRaceStateError("Cannot log a lap after the race has finished")
        if self.in_pit:
            raise InvalidRaceStateError("Cannot log a lap while the car is in the pit")
        if lap_time_ms <= 0:
            raise ValueError("lap_time_ms must be positive")

        self.race_time_ms += lap_time_ms
        self.tyre_temp_c = tyre_temp_at_lap_end_c
        self.current_lap += 1

        if self.current_lap == self.total_laps:
            self.finished = True

        return self._check_tyre_safety()

    def record_speed(self, speed_kmph: float) -> None:
        """FR2: validate and record the car's current speed.
        Raises ValueError if outside the realistic F1 range (250-350 Kmph)."""
        if speed_kmph < MIN_VALID_SPEED_KMPH or speed_kmph > MAX_VALID_SPEED_KMPH:
            raise ValueError(
                f"speed_kmph={speed_kmph} outside valid range "
                f"[{MIN_VALID_SPEED_KMPH}, {MAX_VALID_SPEED_KMPH}]"
            )
        self.last_speed_kmph = speed_kmph

    def _check_tyre_safety(self) -> str:
        if self.tyre_temp_c >= TYRE_MAX_SAFE_TEMP_C:
            return "TYRE_ALERT_PIT_REQUIRED"
        return "OK"

    def enter_pit(self) -> None:
        if self.finished:
            raise InvalidRaceStateError("Race already finished for this car")
        if self.in_pit:
            raise InvalidRaceStateError("Car is already in the pit")
        self.in_pit = True

    def exit_pit(self, pit_duration_ms: int) -> None:
        if not self.in_pit:
            raise InvalidRaceStateError("Car is not currently in the pit")
        if pit_duration_ms < 0:
            raise ValueError("pit_duration_ms cannot be negative")

        self.pit_stop_time_ms += pit_duration_ms
        self.pit_stop_count += 1
        self.tyre_temp_c = TYRE_NOMINAL_TEMP_C  # fresh tyres fitted during the stop
        self.in_pit = False

    def total_time_ms(self) -> int:
        return self.race_time_ms + self.pit_stop_time_ms

    def __repr__(self):
        return (f"Car({self.car_id}, {self.driver_name}, lap={self.current_lap}/"
                f"{self.total_laps}, total_time_ms={self.total_time_ms()}, "
                f"finished={self.finished})")
