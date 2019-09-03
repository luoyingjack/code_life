from flask import abort, g, request

from ...models import Admin


def admin_auth() -> None:
    """管理员身份认证

    Raises:
        werkzeug.exceptions.Unauthorized
    """
    if request.endpoint.split('.')[-1] in ['login']:
        return
    token = request.headers.get(Admin.TOKEN_HEADER)
    if token:
        admin = Admin.get_by_token(token)
        if admin:
            g.admin = admin  # g.admin
            return
    abort(401)
