from flask import Blueprint


bp_admin_ext = Blueprint('bp_admin_ext', __name__)

from . import extensions
