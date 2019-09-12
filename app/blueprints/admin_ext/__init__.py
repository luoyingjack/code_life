from flask import Blueprint


bp_admin_ext = Blueprint('bp_admin_ext', __name__)

appid = 'wxc8f356adb367c7b6'

from . import extensions
