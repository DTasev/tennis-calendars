import os
import requests
import requests.auth
import json
import http.client
import datetime
from functools import reduce
from icalendar import Calendar, Event

from apikeys import *

today = datetime.datetime.now().strftime("%Y-%m-%d")
# today = datetime


def getToday():
    conn = http.client.HTTPSConnection("api.sportradar.us")
    conn.request(
        "GET", f"/tennis-t2/en/schedules/{today}/schedule.json?api_key={sportradar_api_key}")

    res = conn.getresponse()
    data = res.read()

    with open(f"{today}.json", 'wb') as f:
        f.write(data)


class Match:
    def __init__(self, playerOne, playerTwo, time):
        self.playerOne = playerOne
        self.playerTwo = playerTwo
        self.time = time

    def __str__(self):
        return f"{self.playerOne} versus {self.playerTwo} at {self.time.strftime('%Y-%m-%d %H:%M')}"


def group(events: {}, match):
    """
    Groups together all the matches for each event. 
    The matches are grouped per event.
    :param events: The container for the matches for each tournament
    :param match: The data for the current match
    """
    matchTournamentName = match["tournament"]["name"]

    # if there is no previous matches for the event, initialise the list
    if matchTournamentName not in events:
        events[matchTournamentName] = []

    # remove the colon in the timezone, as python's %z doesn't support having a colon there
    timezoneColon = match["scheduled"].rfind(":")
    time = match["scheduled"][:timezoneColon] + match["scheduled"][timezoneColon + 1:]
    time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")

    events[matchTournamentName].append(
        Match(match["competitors"][0]["name"], match["competitors"][1]["name"], time))


def display(cal):
    print(cal.to_ical().strip())


def main(updateCache=False):
    if updateCache:
        getToday()

    data = json.load(open(f"{today}.json", 'rb'))

    events = {}
    # group all the matches by event
    for match in data["sport_events"]:
        group(events, match)

    # dumps the existing data to a file
    # json.dump(gist, open('current.json', 'w'))

    # create the calendar data for each event
    # a calendar file is created per event, this way people can subscribe to certain events
    for eventName, matches in events.items():
        print(eventName)
        cal = Calendar()
        # these only need to be added in a new calendar, but since we're appending to the already existing ones
        # they do not need to be added again. This also means that a new calendar can't be initialised with the current code
        cal.add("NAME", eventName)
        cal.add("prodid", f"-//{eventName}//dtasev.me//")
        for match in matches:
            e = Event()
            e.add("dtstart", match.time)
            e.add("summary", f"{match.playerOne} versus {match.playerTwo}")
            cal.add_component(e)

        with open(f'events/{eventName}.ical', 'w') as f:
            f.write(cal.to_ical().decode("utf-8"))


main()
