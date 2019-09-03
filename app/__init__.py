from flask import Flask

from .config import Config


def create_app() -> Flask:
    """创建flask应用对象"""
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)
    return app
