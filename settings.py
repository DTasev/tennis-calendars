import sys

CALENDAR_IFRAME_BASE = '"<iframe src="https://calendar.google.com/calendar/embed?src={0}" style="border: 0" width="800" height="600" frameborder="0" scrolling="no"></iframe>"'
CALENDAR_EMBED_BASE_URL = "https://calendar.google.com/calendar/embed?src={0}"
CALENDAR_ICAL_BASE_URL = "https://calendar.google.com/calendar/ical/{0}/public/basic.ics"
CALENDAR_URLS_FILENAME = "calendarUrls.md"

SPORTRADAR_IGNORE_TOURNAMENTS = [
    "ITF",
    "ATP Challenger",
    "WTA 125K Indian Wells"
]

LIVESCORE_IGNORE_TOURNAMENTS = [
    "CHALLENGER",
    "ITF",
]

# Settings for Selenium

if sys.platform.startswith("win"):
    CHROME_BINARY_LOCATION = "C:/Program Files (x86)/Google/Chrome Dev/Application/chrome.exe"
    CHROMEDRIVER_LOCATION = "./livescore.in/chromedriver.exe"
elif sys.platform.startswith("linux"):
    CHROME_BINARY_LOCATION = "/usr/bin/google-chrome"
    CHROMEDRIVER_LOCATION = "./livescore.in/chromedriver"
else:
    raise SystemError("The system that the script is being executed on is not supported!")

LIVESCORE_URL = "http://www.livescore.in/free/444741/"
MATCH_EXTEND_MINUTES = 30
MATCH_DEFAULT_DURATION_MINUTES = 90
