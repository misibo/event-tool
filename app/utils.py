from datetime import datetime
from urllib.parse import urlparse
from flask import url_for, request, current_app
import pytz

tz = pytz.timezone('Europe/Zurich')

now = pytz.utc.localize(datetime.utcnow())

def url_back(fallback=None):
    # Get return-URL from query parameters
    url_back = request.args.get("url_back")

    # Get fallback if "url_back"-parameter is not set
    if not url_back:
        if fallback:
            url_back = fallback
            current_app.logger.warning(f"Parameter 'url_back' not defined in query: ({request.url}). Falling back to default: ({url_back}).")
        elif request.referrer and request.method == "GET":
            url_back = request.referrer
            current_app.logger.warning(f"Parameter 'url_back' not defined in query: ({request.url}). Falling back to referrer: ({url_back}).")
        else:
            url_back = request.url
            current_app.logger.warning(f"Parameter 'url_back' not defined in query: ({request.url}). Falling back to current page: ({url_back}).")

    return url_back


def utc_to_localtime(date):
    return pytz.utc.localize(date).astimezone(tz).replace(tzinfo=None)


def localtime_to_utc(date):
    return tz.localize(date).astimezone(pytz.utc).replace(tzinfo=None)

def format_datetime(datetime, format):
    return datetime.astimezone(tz).strftime(format)

def shortdate(datetime):
    return format_datetime(datetime, '%d.%m.%y')

def shortdatetime(datetime):
    return format_datetime(datetime, '%d.%m.%y %H:%M')

def longdate(datetime):
    return format_datetime(datetime, '%a %d. %b %Y')

def longdatetime(datetime):
    return format_datetime(datetime, '%a %d. %b %Y %H:%M')

def pretty_format_date(localtime, long=True):
    if long:
        weekdays = {
            0: 'Montag',
            1: 'Dienstag',
            2: 'Mittwoch',
            3: 'Donnerstag',
            4: 'Freitag',
            5: 'Samstag',
            6: 'Sonntag',
        }
    else:
        weekdays = {
            0: 'Mo',
            1: 'Die',
            2: 'Mi',
            3: 'Do',
            4: 'Fr',
            5: 'Sa',
            6: 'Do',
        }

    if long:
        months = {
            1: 'Januar',
            2: 'Februar',
            3: 'März',
            4: 'April',
            5: 'Mai',
            6: 'Juni',
            7: 'Juli',
            8: 'August',
            9: 'September',
            10: 'Oktober',
            11: 'November',
            12: 'Dezember',
        }
    else:
        months = {
            1: 'Jan',
            2: 'Feb',
            3: 'März',
            4: 'April',
            5: 'Mai',
            6: 'Juni',
            7: 'Juli',
            8: 'Aug',
            9: 'Sep',
            10: 'Okt',
            11: 'Nov',
            12: 'Dez',
        }

    weekday = weekdays[localtime.weekday()]
    month = months[localtime.month]

    return f'{weekday} {localtime.day}. {month}, {localtime.hour:0>2}:{localtime.minute:0>2} Uhr'


if __name__ == '__main__':
    print(pretty_format_date(utc_to_localtime(datetime.utcnow()), long=True))
