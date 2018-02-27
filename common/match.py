import datetime


class MatchTimes:
    def __init__(self, start: datetime.datetime):
        self.start = start


class MatchColors:
    # These contain the Google Calendar Color IDs, which can be seen with
    # colors = service.colors().get().execute()
    CANCELLED = "8"  # Graphite
    # I have no idea what closed means, but it looks like it's when the match ends, however there is also "ended" status
    CLOSED = "3"  # Grape
    LIVE = "10"  # Basil
    # Not updating often enough to care about live matches
    NOT_STARTED = "2"  # Sage
    INTERRUPTED = "1"  # Lavender


class Match:

    def fix_round(self, round: str) -> str:
        # replace any underscores for rounds - "round_of_10" becomes "round of 10"
        # and then capitalise the letters
        return round.replace("_", " ").capitalize()

    def get_color(self, status) -> str:
        if status == "cancelled" or status == "Canc":
            return MatchColors.CANCELLED
        elif status == "closed" or status == "ended" or status == "Fin" or status == "Retired":
            return MatchColors.CLOSED
        elif status == "live" or "S" in status:
            return MatchColors.LIVE
        elif status == "not_started" or status == "" or status == "FRO":
            return MatchColors.NOT_STARTED
        elif status == "Int":
            return MatchColors.INTERRUPTED
        else:
            raise ValueError("We can't handle the status of this match! Problematic state: `" + status + "`")

    def status_from_color(self, color)->str:
        if color == MatchColors.CANCELLED:
            return "Cancelled"
        elif color == MatchColors.CLOSED:
            return "Finished"
        elif color == MatchColors.LIVE:
            return "Live"
        elif color == MatchColors.NOT_STARTED:
            return "Not Started"
        elif color == MatchColors.INTERRUPTED:
            return "Interrupted"

    def is_still_going(self) -> bool:
        return self.status == "live" or "S" in self.status or self.status == "Int"

    def __init__(self, player_one: str, player_two: str, round: str, status: str, time: datetime.datetime):
        self.player_one = player_one
        self.player_two = player_two
        self.round = self.fix_round(round)
        self.status = status
        self.color = self.get_color(status)
        self.time = MatchTimes(time)
        self.name = f"{self.player_one} vs {self.player_two}"

    def __str__(self):
        return f"{self.player_one} versus {self.player_two} at {self.time.start.isoformat()}"
