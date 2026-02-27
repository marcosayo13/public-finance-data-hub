"""Date and time utilities."""

from datetime import datetime, date, timedelta
from typing import Union, Tuple
import pendulum
from pendulum import DateTime


def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> date:
    """Parse date string to date object.

    Args:
        date_str: Date string
        format_str: Format string

    Returns:
        date object
    """
    return datetime.strptime(date_str, format_str).date()


def format_date(d: Union[date, datetime], format_str: str = "%Y-%m-%d") -> str:
    """Format date to string.

    Args:
        d: Date or datetime object
        format_str: Format string

    Returns:
        Formatted date string
    """
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime(format_str)


def get_quarter_end_dates(
    year: int, quarter: int
) -> Tuple[date, date]:
    """Get start and end dates for a quarter.

    Args:
        year: Year
        quarter: Quarter (1-4)

    Returns:
        Tuple of (start_date, end_date)
    """
    if quarter == 1:
        start = date(year, 1, 1)
        end = date(year, 3, 31)
    elif quarter == 2:
        start = date(year, 4, 1)
        end = date(year, 6, 30)
    elif quarter == 3:
        start = date(year, 7, 1)
        end = date(year, 9, 30)
    elif quarter == 4:
        start = date(year, 10, 1)
        end = date(year, 12, 31)
    else:
        raise ValueError(f"Invalid quarter: {quarter}")
    return start, end


def get_year_end_dates(year: int) -> Tuple[date, date]:
    """Get start and end dates for a year.

    Args:
        year: Year

    Returns:
        Tuple of (start_date, end_date)
    """
    return date(year, 1, 1), date(year, 12, 31)


def business_day_offset(d: date, days: int) -> date:
    """Add/subtract business days (Mon-Fri) to a date.

    Args:
        d: Start date
        days: Number of business days to add (positive) or subtract (negative)

    Returns:
        New date
    """
    pend = pendulum.instance(d)
    for _ in range(abs(days)):
        if days > 0:
            pend = pend.add(days=1)
            while pend.weekday() in (5, 6):  # Sat, Sun
                pend = pend.add(days=1)
        else:
            pend = pend.subtract(days=1)
            while pend.weekday() in (5, 6):
                pend = pend.subtract(days=1)
    return pend.date()


def is_business_day(d: date) -> bool:
    """Check if date is a business day (Mon-Fri).

    Args:
        d: Date

    Returns:
        True if business day
    """
    return d.weekday() < 5  # 0-4 = Mon-Fri


def get_last_business_day_of_month(d: date) -> date:
    """Get last business day of the month.

    Args:
        d: Any date in the month

    Returns:
        Last business day of that month
    """
    # Get last day of month
    if d.month == 12:
        last_day = date(d.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(d.year, d.month + 1, 1) - timedelta(days=1)

    # Go back to previous business day if needed
    while not is_business_day(last_day):
        last_day -= timedelta(days=1)

    return last_day


def get_today() -> date:
    """Get today's date.

    Returns:
        Today's date
    """
    return date.today()


def get_now() -> datetime:
    """Get current datetime.

    Returns:
        Current datetime
    """
    return datetime.now()
