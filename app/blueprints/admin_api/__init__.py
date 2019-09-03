from flask import Blueprint

from .hooks import admin_auth
from ...api_utils import *


bp_admin_api = Blueprint('bp_admin_api', __name__)
bp_admin_api.register_error_handler(APIError, handle_api_error)
bp_admin_api.register_error_handler(500, handle_500_error)
bp_admin_api.register_error_handler(400, handle_400_error)
bp_admin_api.register_error_handler(401, handle_401_error)
bp_admin_api.register_error_handler(403, handle_403_error)
bp_admin_api.register_error_handler(404, handle_404_error)
bp_admin_api.before_request(before_api_request)
bp_admin_api.before_request(admin_auth)

from . import v_admin
