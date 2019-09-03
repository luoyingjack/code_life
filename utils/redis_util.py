from os import getenv

from redis import Redis


redis_client = Redis(
    host=getenv('REDIS_HOST') or '127.0.0.1',
    port=int(getenv('REDIS_PORT') or 6379),
    db=int(getenv('REDIS_DB') or 0)
)
