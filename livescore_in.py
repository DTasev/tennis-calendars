import time
import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from common.match import Match
from settings import LIVESCORE_URL, CHROME_BINARY_LOCATION, CHROMEDRIVER_LOCATION, LIVESCORE_IGNORE_TOURNAMENTS


def get_table(browser):
    """
    Tries to get the match table multiple times, sleeping for 1 second each time it fails.
    Abort after 30 seconds. This is done to avoid getting stuck in an infinite loop.
    """
    slept = 0

    while True:
        try:
            if slept > 30:
                raise ConnectionAbortedError("Trying to load the table took too long. Aborting.")
            match_table = browser.find_element_by_class_name("table-main").get_attribute("innerHTML")
            return match_table
        except NoSuchElementException:
            slept += 1
            time.sleep(1)
            pass


def download(today) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.binary_location = CHROME_BINARY_LOCATION
    chrome_driver_binary = CHROMEDRIVER_LOCATION
    browser = webdriver.Chrome(chrome_driver_binary, chrome_options=options)
    browser.get(LIVESCORE_URL)
    match_table = get_table(browser)
    browser.quit()

    with open(f"cache/{today}.html", 'w') as f:
        f.write(match_table)
    return match_table


def load(today):
    with open(f"cache/{today}.html", 'r') as f:
        data = f.readlines()
    parsed_html = BeautifulSoup("\n".join(data), 'html5lib')
    tournament_tables = parsed_html.body.find_all('table', attrs={'class': 'tennis'})

    tournament_data = {}
    datetime_today = datetime.datetime.today()

    for tournament in tournament_tables:
        group_by_tournament(datetime_today, tournament, tournament_data)

    # for tournament_name, matches in tournament_data.items():
    #     print(tournament_name)
    #     print()
    #     for matches in matches:
    #         print(matches)
    #     print("\n------------------------------------\n")

    return tournament_data


def group_by_tournament(datetime_today, tournament, tournament_data):
    tournament_name = f"{tournament.find('span', attrs={'class':'country_part'}).text}{tournament.find('span', attrs={'class':'tournament_part'}).text}"
    # if the tournament is ignored it is not added in the events list
    for ignored in LIVESCORE_IGNORE_TOURNAMENTS:
        if ignored in tournament_name:
            print("Ignored tournament:", tournament_name)
            return

    # create entry for each tournament
    if tournament_name not in tournament_data:
        tournament_data[tournament_name] = []
    tournament_matches = tournament.find('tbody').find_all('tr')
    # the 3rd one is ignored as it is a blank line
    for i in range(0, len(tournament_matches), 3):
        # get the next 2 entries for the matches, the 3rd entry will be a blank line!
        match = tournament_matches[i:i + 2]
        player_one = match[0].find('span', attrs={'class': 'padl'}).text

        # the time and status is only contained in the first row
        time_str = match[0].find('td', attrs={'class': 'time'}).text
        status = match[0].find('td', attrs={'class': 'timer'}).text.strip()

        player_two = match[1].find('span', attrs={'class': 'padl'}).text

        # convert the 24h time to be a datetime object
        time = datetime.datetime.strptime(time_str, "%H:%M")
        # construct the whole datetime for the day, subtract 1 hour as the livescore table is not UTC
        datetime_full = datetime.datetime(datetime_today.year, datetime_today.month, datetime_today.day,
                                          time.hour, time.minute, tzinfo=datetime.timezone.utc) - datetime.timedelta(hours=1)

        tournament_data[tournament_name].append(Match(
            player_one=player_one,
            player_two=player_two,
            round="",
            status=status,
            time=datetime_full))


if __name__ == "__main__":
    from main import today

    load(today)
