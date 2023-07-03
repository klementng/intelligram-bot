import datetime as dt
from datetime import datetime

def round_datetime_mins(tm:datetime, delta:int) -> datetime:
    """
    Round down datetime object to the nearest min

    Parameters
    ----------
    tm : datetime.datetime
        datetime object to be rounded down to

    delta: int
        nearest mins to round to

    Returns
    -------
    datetime.datetime
        Rounded down datetime object
    """

    tm = tm - dt.timedelta(
        minutes=tm.minute % delta,
        seconds=tm.second,
        microseconds=tm.microsecond
    )
    
    return tm


def format_iso_time(isoformat,format = '%Y-%m-%d %H:%M'):
    """
    Accepts time in isoformat. Returns formatted time

    Parameters
    ----------
    isoformat : str
        str in isoformat

    format: str, optional
        new date format, defaults: '%Y-%m-%d %H:%M'

    Returns
    -------
    str
        formatted time string
    """
    return datetime.fromisoformat(isoformat).strftime(format)