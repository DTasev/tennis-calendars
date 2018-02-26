import argparse
import datetime
import json
from typing import List

import requests
import requests.auth
from oauth2client import tools

import gcalendar
from apikeys import GIST_API_KEY, GIST_FILE_ID
from common.match import Match
# from sportradar import download, load
from livescore_in import download, load
from settings import CALENDAR_URLS_FILENAME, CALENDAR_EMBED_BASE_URL, CALENDAR_ICAL_BASE_URL, CALENDAR_IFRAME_BASE

today = datetime.datetime.now().strftime("%Y-%m-%d")


def create_event(service, calendar_id: str, match: Match):
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


def different_times(old, new):
    # the -1 on the existing event returns the datetime string without the Z at the end
    # the rfind on match_time_start returns the datetime string woithout the +00:00 a the end
    # they remove the 2 ways to specify timezone in the standard ISO format
    # the reason we can remove it is that both are guaranteed to be UTC
    return old["start"]["dateTime"][:-1] != new[:new.rfind("+")]


def different_colors(old, new):
    return old["colorId"] != new


def update_event(service, calendar_id: str, match: Match, existing_event: {}):
    match_time_start = match.time.start.isoformat()

    if different_times(existing_event, match_time_start) or different_colors(existing_event, match.color):
        old_start = existing_event["start"]["dateTime"]
        old_color = existing_event["colorId"]
        existing_event["start"] = {"dateTime": match.time.start.isoformat()}
        existing_event["end"] = {"dateTime": match.time.end.isoformat()}
        existing_event["colorId"] = match.color
        update_result = service.events().update(calendarId=calendar_id, eventId=existing_event["id"],
                                                body=existing_event).execute()
        print("Updated event for match:", update_result["summary"], "old start:",
              old_start, "new start:", update_result["start"]["dateTime"], "old_color:", old_color, "new color:", match.color)
    else:
        print("Skipping match as it hasn't changed:", existing_event["summary"])


def update_calendar_events(service, calendar_id, matches: List[Match]):
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
            create_event(service, calendar_id, match)
        else:
            matchEvent = matchEvent[0]
            update_event(service, calendar_id, match, matchEvent)


def create_calendar(service, tournament_name):
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


def generate_calendar_urls(service):
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

### Notes:
- The ICAL will be refreshed whenever your calendar application decides to query for changes. This can differ. On Google it changes are quickly reflected.
- This is still being tested and something will probably fail.

<hr/>

### Calendar Event Colours (in Google)
- Cancelled is Graphite (gray)
- Finished is Lavender (purple-ish)
- Not started is Sage (blue-ish green-ish)
- Live/started is Basil (green)

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
    gistResponse = requests.patch(f'https://api.github.com/gists/{GIST_FILE_ID}',
                                  auth=requests.auth.HTTPBasicAuth("DTasev", GIST_API_KEY),
                                  data=json.dumps(gist))
    print(gistResponse)


def main(args):
    if args.fetch:
        download(today)

    # get calendars
    service = gcalendar.auth(args)
    calendarsListResult = service.calendarList().list().execute()
    calendarsList = calendarsListResult.get('items', None)
    calendars = {}
    print("Calendars downloaded.")

    # create a dictionary for every calendar
    for c in calendarsList:
        calendars[c["summary"]] = {"id": c["id"]}

    print("Calendars moved to dictionary.")

    tournament = load(today)

    id = 0
    # for every tournament
    for tournament_name, matches in tournament.items():
        print("Processing tournament:", tournament_name)
        # check if there is a calendar for the tournament
        if tournament_name not in calendars:
            print("Calendar not found, creating a new one...")
            calendar_id = create_calendar(service, tournament_name)
        else:
            print("Calendar already exists.")
            calendar_id = calendars[tournament_name]["id"]
        update_calendar_events(service, calendar_id, matches)

        # Process every entry from the remote data. This is used to limit how many entries are processed
        # during development. If --no-limit is not specified, then only the first 10 will be processed
        if not args.no_limit:
            if id == 10:
                break
            id += 1

    print("Generating calendar URLs.")
    generate_calendar_urls(service)


def setup_args() -> argparse.ArgumentParser:
    # add arguments for google authentication
    parser = argparse.ArgumentParser(parents=[tools.argparser])

    # additional arguments for the package
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--no-limit", action="store_true")
    return parser


if __name__ == "__main__":
    parser = setup_args()
    args = parser.parse_args()
    main(args)
