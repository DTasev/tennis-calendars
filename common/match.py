import datetime
from enum import Enum


class Times:
    def __init__(self, start: datetime.datetime):
        self.start = start


class Colors:
    # These contain the Google Calendar Color IDs, which can be seen with
    # colors = service.colors().get().execute()
    CANCELLED = "8"  # Graphite
    CLOSED = "3"  # Grape
    LIVE = "10"  # Basil
    NOT_STARTED = "2"  # Sage
    INTERRUPTED = "1"  # Lavender


class Status(Enum):
    CANCELLED = "Cancelled"
    CLOSED = "Closed"
    LIVE = "Live"
    NOT_STARTED = "Not Started"
    INTERRUPTED = "Interrupted"

    @staticmethod
    def from_status(status: str):
        if status == "cancelled" or status == "Canc":
            return Status.CANCELLED
        elif status == "closed" or status == "ended" or status == "Fin" or status == "Retired":
            return Status.CLOSED
        elif status == "live" or "S" in status:
            return Status.LIVE
        elif status == "not_started" or status == "" or status == "FRO":
            return Status.NOT_STARTED
        elif status == "Int":
            return Status.INTERRUPTED
        else:
            raise ValueError("We can't handle the status of this match! Problematic state: `" + status + "`")


class Match:

    def fix_round(self, round: str) -> str:
        # replace any underscores for rounds - "round_of_10" becomes "round of 10"
        # and then capitalise the letters
        return round.replace("_", " ").capitalize()

    def get_color(self, status: Status) -> str:
        if status == Status.CANCELLED:
            return Colors.CANCELLED
        elif status == Status.CLOSED:
            return Colors.CLOSED
        elif status == Status.LIVE:
            return Colors.LIVE
        elif status == Status.NOT_STARTED:
            return Colors.NOT_STARTED
        elif status == Status.INTERRUPTED:
            return Colors.INTERRUPTED
        else:
            raise ValueError("There is a status that doesn't have a color! Problematic status: `" + str(status) + "`")

    def status_from_color(self, color: str) -> Status:
        if color == Colors.CANCELLED:
            return Status.CANCELLED
        elif color == Colors.CLOSED:
            return Status.CLOSED
        elif color == Colors.LIVE:
            return Status.LIVE
        elif color == Colors.NOT_STARTED:
            return Status.NOT_STARTED
        elif color == Colors.INTERRUPTED:
            return Status.INTERRUPTED
        else:
            raise ValueError("There is a COLOR that doesn't have a STATUS! Problematic color: `" + color + "`")

    def is_still_going(self) -> bool:
        return self._status == Status.LIVE or self._status == Status.INTERRUPTED

    def is_finished(self) -> bool:
        return self._status == Status.CLOSED or self._status == Status.CANCELLED

    def __init__(self, player_one: str, player_two: str, round: str, status: str, time: datetime.datetime):
        self.player_one = player_one
        self.player_two = player_two
        self.round = self.fix_round(round)
        self._status = Status.from_status(status)
        self.color = self.get_color(self._status)
        self.time = Times(time)
        self.name = f"{self.player_one} vs {self.player_two}"

    def __str__(self):
        return f"{self.player_one} versus {self.player_two} at {self.time.start.isoformat()}"
