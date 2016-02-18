#datetime to unix test
import calendar
from datetime import datetime


def timestamp_to_datetime(ts):
    return datetime.utcfromtimestamp(float(ts))


def datetime_to_timestamp(dt):
    return calendar.timegm(dt.timetuple())

#print datetime_to_timestamp('2015-09-07 20:34:41')

times
