import datetime
import http.client
import json

from apikeys import sportradar_api_key
from settings import SPORTRADAR_IGNORE_TOURNAMENTS
from common.match import Match


def download(today):
    conn = http.client.HTTPSConnection("api.sportradar.us")
    conn.request(
        "GET", f"/tennis-t2/en/schedules/{today}/schedule.json?api_key={sportradar_api_key}")

    res = conn.getresponse()
    data = res.read()

    with open(f"cache/{today}.json", 'wb') as f:
        f.write(data)
    print("Downloaded today's matches data from Sportradar.")


def load(today):
    # get tennis matches and group_by_tournament by tournament
    data = json.load(open(f"cache/{today}.json", 'rb'))
    print("Loaded data from cache.")

    tournament = {}

    # group_by_tournament all the matches by event
    for match in data["sport_events"]:
        group_by_tournament(tournament, match)

    print("Grouped matches by tournament.")
    return tournament


def group_by_tournament(events: {}, match):
    """
    Groups together all the matches for each event.
    The matches are grouped per event.
    :param events: The container for the matches for each tournament
    :param match: The data for the current match
    """
    match_tournament_name = match["tournament"]["name"]

    # if the tournament is ignored it is not added in the events list
    for ignored in SPORTRADAR_IGNORE_TOURNAMENTS:
        if ignored in match_tournament_name:
            return
    # if there is no previous matches for the event, initialise the list
    if match_tournament_name not in events:
        events[match_tournament_name] = []

    # remove the colon in the timezone, as python's %z doesn't support having a colon there
    timezone_colon = match["scheduled"].rfind(":")
    time = match["scheduled"][:timezone_colon] + match["scheduled"][timezone_colon + 1:]
    time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")

    round = match["tournament_round"]["name"]
    status = match["status"]

    events[match_tournament_name].append(
        Match(player_one=match["competitors"][0]["name"],
              player_two=match["competitors"][1]["name"],
              round=round,
              status=status,
              time=time))
