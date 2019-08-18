import pytz
from datetime import datetime, timedelta

mytz = pytz.timezone('Europe/Zurich')


def utc_to_localtime(date):
    return pytz.utc.localize(date).astimezone(mytz).replace(tzinfo=None)


def localtime_to_utc(date):
    return mytz.localize(date).astimezone(pytz.utc).replace(tzinfo=None)


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
