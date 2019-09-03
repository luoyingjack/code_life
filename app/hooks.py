from flask import abort, current_app, g, request

from .models import db


def before_app_request() -> None:
    """请求前全局钩子函数

    Raises:
        werkzeug.exceptions.NotFound
    """
    if not request.blueprint:
        abort(404)
    current_app.logger.debug('{0.method} {0.full_path} {0.headers!r} {0.data!r}'.format(request))
    g.ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-Ip')  # g.ip
    db.connect(reuse_if_open=True)


def teardown_app_request(e: Exception=None) -> None:
    """请求后全局钩子函数"""
    db.close()
