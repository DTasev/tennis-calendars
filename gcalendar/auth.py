import datetime
import os

import httplib2
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


def get_credentials(args):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, args)
        print('Storing credentials to ' + credential_path)
    return credentials


def auth(args):
    credentials = get_credentials(args)
    http = credentials.authorize(httplib2.Http())
    return discovery.build('calendar', 'v3', http=http)


def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    service = auth()

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    eventsResult = service.events().list(
        calendarId='2pr9a9qr02j9lamllukocqqsec@group_by_tournament.calendar.google.com', timeMin=now, maxResults=10,
        singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'], event)

    calendars = service.calendarList().list().execute()
    cals = calendars.get('items', "No calendars were found")
    for c in cals:
        print("Name:", c["summary"], "id: ", c["id"])

    # name = "ATP Test Calendar"
    # calendarBody = {
    #     "summary": name
    # }
    # print("Creating calendar", name)
    # print(service.calendars().insert(body=calendarBody).execute())
    # created_event = service.events().quickAdd(calendarId="2pr9a9qr02j9lamllukocqqsec@group_by_tournament.calendar.google.com",
    #                                           text='API Tennis on 24/02/2018 23:30-00:00').execute()

    # print(created_event['id'])


if __name__ == '__main__':
    main()
