import datetime
from enum import Enum


class MatchTimes:
    def __init__(self, start: datetime.datetime):
        self.start = start


class MatchColors:
    # These contain the Google Calendar Color IDs, which can be seen with
    # colors = service.colors().get().execute()
    CANCELLED = "8"  # Graphite
    CLOSED = "3"  # Grape
    LIVE = "10"  # Basil
    NOT_STARTED = "2"  # Sage
    INTERRUPTED = "1"  # Lavender


class MatchStatus(Enum):
    CANCELLED = "Cancelled"
    CLOSED = "Closed"
    LIVE = "Live"
    NOT_STARTED = "Not Started"
    INTERRUPTED = "Interrupted"

    @staticmethod
    def from_status(status: str):
        if status == "cancelled" or status == "Canc":
            return MatchStatus.CANCELLED
        elif status == "closed" or status == "ended" or status == "Fin" or status == "Retired":
            return MatchStatus.CLOSED
        elif status == "live" or "S" in status:
            return MatchStatus.LIVE
        elif status == "not_started" or status == "" or status == "FRO":
            return MatchStatus.NOT_STARTED
        elif status == "Int":
            return MatchStatus.INTERRUPTED
        else:
            raise ValueError("We can't handle the status of this match! Problematic state: `" + status + "`")


class Match:

    def fix_round(self, round: str) -> str:
        # replace any underscores for rounds - "round_of_10" becomes "round of 10"
        # and then capitalise the letters
        return round.replace("_", " ").capitalize()

    def get_color(self, status: MatchStatus) -> str:
        if status == MatchStatus.CANCELLED:
            return MatchColors.CANCELLED
        elif status == MatchStatus.CLOSED:
            return MatchColors.CLOSED
        elif status == MatchStatus.LIVE:
            return MatchColors.LIVE
        elif status == MatchStatus.NOT_STARTED:
            return MatchColors.NOT_STARTED
        elif status == MatchStatus.INTERRUPTED:
            return MatchColors.INTERRUPTED
        else:
            raise ValueError("There is a status that doesn't have a color! Problematic status: `" + str(status) + "`")

    def status_from_color(self, color: str) -> MatchStatus:
        if color == MatchColors.CANCELLED:
            return MatchStatus.CANCELLED
        elif color == MatchColors.CLOSED:
            return MatchStatus.CLOSED
        elif color == MatchColors.LIVE:
            return MatchStatus.LIVE
        elif color == MatchColors.NOT_STARTED:
            return MatchStatus.NOT_STARTED
        elif color == MatchColors.INTERRUPTED:
            return MatchStatus.INTERRUPTED
        else:
            raise ValueError("There is a COLOR that doesn't have a STATUS! Problematic color: `" + color + "`")

    def is_still_going(self) -> bool:
        return self._status == MatchStatus.LIVE or self._status == MatchStatus.INTERRUPTED

    def is_finished(self) -> bool:
        return self._status == MatchStatus.CLOSED or self._status == MatchStatus.CANCELLED

    def __init__(self, player_one: str, player_two: str, round: str, status: str, time: datetime.datetime):
        self.player_one = player_one
        self.player_two = player_two
        self.round = self.fix_round(round)
        self._status = MatchStatus.from_status(status)
        self.color = self.get_color(self._status)
        self.time = MatchTimes(time)
        self.name = f"{self.player_one} vs {self.player_two}"

    def __str__(self):
        return f"{self.player_one} versus {self.player_two} at {self.time.start.isoformat()}"
