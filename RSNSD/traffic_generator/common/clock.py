"""
Simulation Clock

Provides time-dependent evolution of the simulation environment.
Author: RSNSD
"""

from datetime import datetime, timedelta

class SimulationClock:
    """
    Tracks the progression of time throughout the simulation.
    """

    def __init__(self, start_time: datetime, step_minutes: int = 5):
        self.current_time = start_time
        self.step_minutes = step_minutes

    def tick(self) -> datetime:
        """Advance the clock by one time slot."""
        self.current_time += timedelta(minutes=self.step_minutes)
        return self.current_time

    @property
    def hour(self) -> int:
        return self.current_time.hour

    @property
    def minute(self) -> int:
        return self.current_time.minute

    @property
    def time_string(self) -> str:
        return self.current_time.strftime("%H:%M")

    @property
    def is_rush_hour(self) -> bool:
        """Morning and evening rush hours."""
        return (8 <= self.hour < 10) or (17 <= self.hour < 19)

    @property
    def is_night(self) -> bool:
        """Low activity nighttime."""
        return (23 <= self.hour) or (self.hour < 5)

    @property
    def is_school_hours(self) -> bool:
        """Active school duration."""
        return (9 <= self.hour < 15)

    def get_time_multiplier(self) -> float:
        """
        Returns a load multiplier based on the time of day.
        """
        if self.is_rush_hour:
            return 1.0
        elif self.is_night:
            return 0.2
        else:
            # Gradually adjust depending on time, or just use 0.6
            return 0.6
