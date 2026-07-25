"""
payout_service.py
FR7: trigger the sponsor's cash-reward payout to the race winner.

This service is intentionally separate from the race domain so payout logic
can evolve independently from lap timing and tyre rules.
"""

from typing import Optional

from car import Car

SPONSOR_NAME = "Prime Motors Sponsorship"
CASH_REWARD_AMOUNT = 500_000


class PayoutError(Exception):
    """Raised when a payout is requested in an invalid state."""


class PayoutService:
    def __init__(self):
        self._paid_car_ids = set()

    def trigger_payout(self, winner: Optional[Car]) -> dict:
        """Issue the sponsor payout to the winning car exactly once per race."""
        if winner is None:
            raise PayoutError("Cannot trigger payout: no winner determined yet")
        if winner.car_id in self._paid_car_ids:
            raise PayoutError(f"Payout already issued to car {winner.car_id}")

        self._paid_car_ids.add(winner.car_id)
        return {
            "car_id": winner.car_id,
            "driver_name": winner.driver_name,
            "amount": CASH_REWARD_AMOUNT,
            "sponsor": SPONSOR_NAME,
            "status": "PAID",
        }

    def has_been_paid(self, car_id: str) -> bool:
        return car_id in self._paid_car_ids
