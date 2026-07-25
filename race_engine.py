"""
race_engine.py
Determines the winner of a Formula One race from a list of Car objects.
"""

from typing import Optional

from car import Car


class RaceEngine:
    def __init__(self, cars: list[Car]):
        self.cars = cars

    def get_winner(self) -> Optional[Car]:
        """Winner = lowest total_time_ms among cars that have finished all laps."""
        finished_cars = [c for c in self.cars if c.finished]
        if not finished_cars:
            return None
        return min(finished_cars, key=lambda c: c.total_time_ms())
