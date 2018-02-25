import argparse
import datetime
import http.client
import json
from typing import List

import requests
import requests.auth
from oauth2client import tools

import gcalendar
from apikeys import *

today = datetime.datetime.now().strftime("%Y-%m-%d")
EVENT_DURATION_MINUTES = 90

CALENDAR_IFRAME_BASE = '"<iframe src="https://calendar.google.com/calendar/embed?src={0}" style="border: 0" width="800" height="600" frameborder="0" scrolling="no"></iframe>"'
CALENDAR_EMBED_BASE_URL = "https://calendar.google.com/calendar/embed?src={0}"
CALENDAR_ICAL_BASE_URL = "https://calendar.google.com/calendar/ical/{0}/public/basic.ics"
CALENDAR_URLS_FILENAME = "calendarUrls.md"

IGNORE_TOURNAMENTS = [
    "ITF",
    "ATP Challenger",
    "WTA 125K Indian Wells"
]

def getToday():
    conn = http.client.HTTPSConnection("api.sportradar.us")
    conn.request(
        "GET", f"/tennis-t2/en/schedules/{today}/schedule.json?api_key={sportradar_api_key}")

    res = conn.getresponse()
    data = res.read()

    with open(f"cache/{today}.json", 'wb') as f:
        f.write(data)


class MatchTimes:
    def __init__(self, start: datetime.datetime, end: datetime.datetime):
        self.start = start
        self.end = end


class MatchColors:
    # These contain the Google Calendar Color IDs, which can be seen with
    # colors = service.colors().get().execute()
    CANCELLED = "8"  # Graphite
    # I have no idea what closed means, but it looks like it's when the match ends, however there is also "ended" status
    CLOSED = "3"  # Lavender
    NOT_STARTED = "10"  # Basil
    # Not updating often enough to care about live matches
    # LIVE = "2" # Sage


class Match:

    def fix_round(self, round: str) -> str:
        # replace any underscores for rounds - "round_of_10" becomes "round of 10"
        # and then capitalise the letters
        return round.replace("_", " ").capitalize()

    def get_color(self, status) -> str:
        if status == "cancelled":
            return MatchColors.CANCELLED
        elif status == "closed" or status == "ended":
            return MatchColors.CLOSED
        elif status == "not_started" or status == "live":
            return MatchColors.NOT_STARTED
        else:
            raise ValueError("We can't handle the status of this match! Problematic state: " + status)

    def __init__(self, player_one: str, player_two: str, round: str, status: str, time: datetime.datetime):
        self.player_one = player_one
        self.player_two = player_two
        self.round = self.fix_round(round)
        self.status = status
        self.color = self.get_color(status)
        self.time = MatchTimes(time, time + datetime.timedelta(minutes=EVENT_DURATION_MINUTES))
        self.name = f"{self.round} - {self.player_one} vs {self.player_two} - {self.status.replace('_', ' ').title()}"

    def __str__(self):
        return f"{self.player_one} versus {self.player_two} at {self.time.start.isoformat()}"


def group_by_tournament(events: {}, match):
    """
    Groups together all the matches for each event. 
    The matches are grouped per event.
    :param events: The container for the matches for each tournament
    :param match: The data for the current match
    """
    match_tournament_name = match["tournament"]["name"]

    # if the tournament is ignored it is not added in the events list
    for ignored in IGNORE_TOURNAMENTS:
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


def createEvent(service, calendar_id: str, match: Match):
    # use 12-hour format so that Google can correctly create events throughout the night
    # otherwise it assumes things like 02:45 (2 after midnight in 24-hour clock) to be 2 in the afternoon,
    # as it is more likely that people will create events for the day than the night
    event = {
        "summary": match.name,
        "start": {
            "dateTime": match.time.start.isoformat()
        },
        "end": {
            "dateTime": match.time.end.isoformat()
        },
        "maxAttendees": "100",
        "guestsCanInviteOthers": "true",
        "guestsCanSeeOtherGuests": "true",
        "anyoneCanAddSelf": "true",
        "colorId": match.color
    }
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print("Created event for match:", created_event["summary"])


def updateEvent(service, calendar_id: str, match: Match, existing_event: {}):
    match_time_start = match.time.start.isoformat()
    # the -1 on the existing event returns the datetime string without the Z at the end
    # the rfind on match_time_start returns the datetime string woithout the +00:00 a the end
    # they remove the 2 ways to specify timezone in the standard ISO format
    # the reason we can remove it is that both are guaranteed to be UTC
    if existing_event["start"]["dateTime"][:-1] != match_time_start[:match_time_start.rfind("+")]:
        existing_event["start"] = {"dateTime": match.time.start.isoformat()}
        existing_event["end"] = {"dateTime": match.time.end.isoformat()}
        existing_event["colorId"] = match.color
        update_result = service.events().update(calendarId=calendar_id, eventId=existing_event["id"],
                                                body=existing_event).execute()
        print("Updated event for match:", update_result["summary"])
    else:
        print("Skipping match as it hasn't changed:", existing_event["summary"])


def updateExistingCalendar(service, calendar_id, matches: List[Match]):
    today = datetime.datetime.today()
    # used to query events only for today
    midnight = datetime.datetime(today.year, today.month, today.day, 0, 0)
    # convert to the ISO format string with Z at the end to signify UTC timezone
    midnight = midnight.isoformat() + "Z"

    # get all events for today, hopefully 100 is big enough for a calendar
    # WARNING this also means that if this code is executed for past days, then the events WILL NEVER BE UPDATED
    # as they are never queried and duplicates will be created instead of updating the time!
    eventsResult = service.events().list(calendarId=calendar_id, maxResults=100, timeMin=midnight).execute()
    events = eventsResult.get('items', None)
    print("Retrieved events for calendar.")

    # TODO batch request https://developers.google.com/google-apps/calendar/batch
    for match in matches:
        matchEvent = [event for event in events if event["summary"] == match.name]
        if len(matchEvent) > 1:
            raise ValueError("There is more than one event with matching names, and there should only be one!")

        if len(matchEvent) == 0:
            createEvent(service, calendar_id, match)
        else:
            matchEvent = matchEvent[0]
            updateEvent(service, calendar_id, match, matchEvent)
        return


def createCalendar(service, tournament_name):
    calendarBody = {
        "summary": tournament_name
    }
    print("Creating calendar: ", tournament_name)
    createdCalendar = service.calendars().insert(body=calendarBody).execute()
    publicPermissions = {
        "role": "reader",
        "scope": {
            "type": "default"
        }
    }

    print("Adding public READ permission.")
    service.acl().insert(calendarId=createdCalendar["id"], body=publicPermissions).execute()
    return createdCalendar["id"]


def generateCalendarUrls(service):
    calendarsListResult = service.calendarList().list().execute()
    calendarsList = calendarsListResult.get('items', None)
    fileData = [
        """### Importing a calendar:
1. Copy ICAL link from below.
1. Add calendar by URL
    - Google: Go to [Add by URL](https://calendar.google.com/calendar/b/1/r/settings/addbyurl)
        - Name is read automatically
    - Web Outlook: Go to your [Calendar](https://outlook.live.com/owa/?path=/calendar/view/Day)
        - Near the top of the screen there should be `Add Calendar`
        - After clicking it, there should be `From the Internet`
        - Name will be read automatically, although there is an escape character `\` before each coma
    - Web Outlook BETA: Go to your [Calendar](https://outlook.live.com/calendar/#/view/day/)
        - In the Calendar list on the left there should be `Discover Calendars`
        - At the bottom of the `Discover Calendars` window there should be `From web`
        - Name must be manually added
    - Windows 10 Calendar:
        - Can't add calendar from URL as far as I am aware
    - Office Outlook 2016:
        - Find `Open Calendar` button, should be near to top, it might be folded in a `Manage Calendars` folder
            - Alternatively go to `Folder -> Open Calendar`
        - After clicking it there should be `From Internet`
1. Paste link and click add/import.
<hr/>
"""
    ]
    for calendar in calendarsList:
        # remove primary calendar, and #contacts and #holidays
        if "@gmail" not in calendar["id"] and "#" not in calendar["id"]:
            fileData.append(f"""### {calendar["summary"]}
* ICAL: {CALENDAR_ICAL_BASE_URL.format(calendar["id"])}
* Embed: {CALENDAR_EMBED_BASE_URL.format(calendar["id"])}
* IFRAME: {CALENDAR_IFRAME_BASE.format(calendar["id"])}
<hr/>
""")

    fileData = "\n".join(fileData)
    with open(CALENDAR_URLS_FILENAME, 'w') as f:
        f.write(fileData)

    gist = {
        "description": "Tennis Calendars",
        "public": "true",
        "files": {
            CALENDAR_URLS_FILENAME: {
                "content": fileData
            }
        }

    }
    print("Uploading calendar urls to GIST.")
    gistResponse = requests.patch(f'https://api.github.com/gists/{gist_file_id}',
                                  auth=requests.auth.HTTPBasicAuth("DTasev", gist_api_key),
                                  data=json.dumps(gist))
    print(gistResponse)


def main(args):
    if args.fetch:
        getToday()
        print("Downloaded today's matches data from Sportradar.")

    # get calendars
    service = gcalendar.auth(args)
    calendarsListResult = service.calendarList().list().execute()
    calendarsList = calendarsListResult.get('items', None)
    calendars = {}
    print("Calendars downloaded.")

    # create a dictionary for every calendar
    for c in calendarsList:
        calendars[c["summary"]] = {"id": c["id"]}

    print(calendars)
    print("Calendars moved to dictionary.")
    # get tennis matches and group_by_tournament by tournament
    data = json.load(open(f"cache/{today}.json", 'rb'))
    print("Loaded data from cache.")

    tournament = {}
    # group_by_tournament all the matches by event
    for match in data["sport_events"]:
        group_by_tournament(tournament, match)
    print("Grouped matches by tournament.")

    id = 0
    # for every tournament
    for tournament_name, matches in tournament.items():
        print("Processing tournament:", tournament_name)
        # check if there is a calendar for the tournament
        if tournament_name not in calendars:
            print("Calendar not found, creating a new one...")
            calendar_id = createCalendar(service, tournament_name)
        else:
            print("Calendar already exists.")
            calendar_id = calendars[tournament_name]["id"]
        updateExistingCalendar(service, calendar_id, matches)

        # Process every entry from the remote data. This is used to limit how many entries are processed
        # during development. If --no-limit is not specified, then only the first 10 will be processed
        if not args.no_limit:
            if id == 10:
                break
            id += 1

    print("Generating calendar URLs.")
    generateCalendarUrls(service)


def setupArgs() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--no-limit", action="store_true")
    return parser


if __name__ == "__main__":
    parser = setupArgs()
    args = parser.parse_args()
    main(args)
