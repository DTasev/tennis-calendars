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


# getToday()

def fixName(playerName: str) -> str:
    print(playerName)

    # if the match is doubles, then split each player's name
    playerName = playerName.split(' / ') if ' / ' in playerName else [playerName]

    finalNames = []
    # for each player's name split on coma to convert to Firstname Lastname format
    for name in playerName:
        if ", " in name:
            name = name.split(", ")
            finalNames.append(name[1] + " " + name[0])
    return " / ".join(finalNames)


class Match:
    def __init__(self, playerOne, playerTwo, time):
        self.playerOne = playerOne
        self.playerTwo = playerTwo
        self.time = time

    def __str__(self):
        return f"{self.playerOne} versus {self.playerTwo} at {self.time.strftime('%Y-%m-%d %H:%M')}"


def group(events, e):
    if e["tournament"]["name"] not in events:
        events[e["tournament"]["name"]] = []

    timezoneColon = e["scheduled"].rfind(":")
    time = e["scheduled"][:timezoneColon] + e["scheduled"][timezoneColon + 1:]
    time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")
    events[e["tournament"]["name"]].append(Match(e["competitors"][0]["name"], e["competitors"][1]["name"], time))


def display(cal):
    print(cal.to_ical().strip())


def main(keepOld=True):
    data = json.load(open(f"{today}.json", 'rb'))

    events = {}
    # group all the matches by event
    for match in data["sport_events"]:
        group(events, match)

    # get the current calendar data in the GIST
    currentData = json.loads(requests.get(f'https://api.github.com/gists/{gist_id}',
                                          auth=requests.auth.HTTPBasicAuth("DTasev", gist_api_key)).content)

    # remove all of github's metadata that can't be sent back in the PATCH request
    onlyContentData = {}
    for entry, value in currentData["files"].items():
        onlyContentData[entry] = {"content": value["content"]}

    gist = {
        "description": currentData["description"],
        "public": "true",
        "files": onlyContentData
    }

    # dumps the existing data to a file
    # json.dump(gist, open('current.json', 'w'))

    # create the calendar data for each event
    # a calendar file is created per event, this way people can subscribe to certain events
    for eventName, matches in events.items():
        print(eventName)
        cal = Calendar()
        # these only need to be added in a new calendar, but since we're appending to the already existing ones
        # they do not need to be added again. This also means that a new calendar can't be initialised with the current code
        # cal.add("NAME", eventName)
        # cal.add("prodid", f"-//{eventName}//dtasev.me//")
        for match in matches:
            e = Event()
            e.add("dtstart", match.time)
            e.add("summary", f"{match.playerOne} versus {match.playerTwo}")
            cal.add_component(e)

        newMatchData = cal.to_ical().decode("utf-8")

        oldMatch = gist["files"].get(f"{eventName}.ical", None)
        # if there is existing old match data, then append the new data at the end, this requires slight restructuring to remove the beginning
        # BEGIN:VCALENDAR from the new data, and the trailing END:VCALENDAR from the OLD data.
        if oldMatch:
            oldMatchData = oldMatch["content"]

            # remove the BEGIN:VCALENDAR from the data. This needs to be removed, as the new match data will be appended at the end
            # of the old one, and we can't have 2 BEGIN:VCALENDARS
            newMatchData = newMatchData[newMatchData.find("\n") + 1:]

            # strip removes a trailing new line, then rfind finds the start of the last line, which will be removed
            calendarEndLinePosition = oldMatchData.strip().rfind("\n")

            # remove the END:VCALENDAR from the original string, append the new match data on the end. The newMatchData contains the necessary
            # END:VCALENDAR string. This appends the new events to the old ones, forming a larger calendar
            gist["files"][f"{eventName}.ical"]["content"] = oldMatchData[:calendarEndLinePosition + 1] + newMatchData

        else:  # if there is NO data for this tournament, then create a new entry
            gist["files"][f"{eventName}.ical"] = {"content": newMatchData}

    json.dump(gist, open('new.json', 'w'))
    return
    # TODO update ical tomorrow
    r = requests.patch(f'https://api.github.com/gists/{gist_id}',
                       auth=requests.auth.HTTPBasicAuth("DTasev", gist_api_key), data=json.dumps(gist))
    print(r, r.reason)


main()
