from datetime import date
from decimal import Decimal

from flask.json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    """自定义JSONEncoder"""

    def default(self, o):
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Decimal):
            f = float(o)
            return int(f) if f.is_integer() else f
        try:
            iterator = iter(o)
        except TypeError:
            pass
        else:
            return list(iterator)
        return super().default(o)
