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


def group(events, e):
    if e["tournament"]["name"] not in events:
        events[e["tournament"]["name"]] = []

    timezoneColon = e["scheduled"].rfind(":")
    time = e["scheduled"][:timezoneColon] + e["scheduled"][timezoneColon + 1:]
    time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z")
    events[e["tournament"]["name"]].append(
        (
            e["competitors"][0]["name"],
            e["competitors"][1]["name"],
            time,
        )
    )


def display(cal):
    print(cal.to_ical().strip())


def main():
    data = json.load(open(f"{today}.json", 'rb'))
    # print(data["sport_events"][-1])
    # for entry in data["sport_events"]:
    #     timezoneColon=entry["scheduled"].rfind(":")
    #     time=entry["scheduled"][:timezoneColon] + entry["scheduled"][timezoneColon + 1:]
    #     print(datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z"))

    # print(data["sport_events"][0].keys())

    events = {}
    # group all the matches by event
    for match in data["sport_events"]:
        group(events, match)

    gist = {
        "description": "Tennis Calendars",
        "public": "true"
    }

    files = {}
    for eventName, matches in events.items():
        print(eventName)
        cal = Calendar()
        cal.add("NAME", eventName)
        cal.add("prodid", f"-//{eventName}//dtasev.me//")
        print("\n----------------------------------------")
        for match in matches:
            print(match)
            e = Event()
            e.add("dtstart", match[2])
            e.add("summary", f"{match[0]} versus {match[1]}")
            cal.add_component(e)

        files[f"{eventName}.ical"] = {
            "content": cal.to_ical().decode("utf-8")
        }

    gist["files"] = files
    print(gist)
    r = requests.patch(f'https://api.github.com/gists/{gist_id}',
                       auth=requests.auth.HTTPBasicAuth("DTasev", gist_api_key), data=json.dumps(gist))
    print(r, r.reason)


main()
