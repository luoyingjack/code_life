from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Tuple


def calc_time_interval(time_str: str) -> Tuple[datetime, datetime]:
    """计算起止时间

    Args:
        time_str: 表示时间段的字符串：
            'today' - 今天，'week' - 本周，'month' - 本月，'year' - 今年；
            也可以将起止时间分别以ISO标准时间格式表示，并用'~'连接后传入

    Raises:
        ValueError
    """
    today = date.today()
    year, month, day = today.year, today.month, today.day
    if time_str == 'today':
        start = datetime(year, month, day)
        end = start + timedelta(days=1, microseconds=-1)
    elif time_str == 'week':
        start = datetime(year, month, day) - timedelta(days=today.weekday())
        end = start + timedelta(weeks=1, microseconds=-1)
    elif time_str == 'month':
        _, days = monthrange(year, month)
        start = datetime(year, month, 1)
        end = start + timedelta(days=days, microseconds=-1)
    elif time_str == 'year':
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1) + timedelta(microseconds=-1)
    else:
        start, end = map(datetime.fromisoformat, time_str.split('~'))
        if start > end:
            raise ValueError('The start-time is later than the end-time')
    return start, end
