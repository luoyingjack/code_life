from flask import g

from . import bp_admin_api
from ...api_utils import *
from ...models import Admin


@bp_admin_api.route('/admin/login/', methods=['PUT'])
def login():
    """
    @apiVersion 1.0.0
    @api {PUT} /api/admin/login/ 登录
    @apiName admin_login
    @apiGroup admin_Admin

    @apiParam {String} username 用户名
    @apiParam {String} password 密码

    @apiSuccess (响应数据) {String} token 身份令牌
    @apiSuccess (响应数据) {Object} admin 管理员对象（参考admin对象）
    @apiUse admin_obj

    @apiUse e1203
    @apiUse e1204
    @apiUse e1301
    @apiUse e1302
    """
    username, password = map(g.json.get, ['username', 'password'])
    claim_args(1203, username, password)
    claim_args_str(1204, username, password)
    admin = Admin.get_by_username(username)
    claim_args_true(1301, admin)
    claim_args_true(1302, admin.check_password(password))

    admin.login(g.ip or '')
    data = {
        'token': admin.gen_token(),
        'admin': admin.to_dict()
    }
    return api_success_response(data)


@bp_admin_api.route('/current_admin/', methods=['GET'])
def get_current_admin():
    """
    @apiVersion 1.0.0
    @api {GET} /api/current_admin/ 获取当前管理员详情
    @apiName admin_get_current_admin
    @apiGroup admin_Admin
    @apiPermission admin

    @apiSuccess (响应数据) {Object} admin 管理员对象（参考admin对象）
    @apiUse admin_obj
    """
    data = {
        'admin': g.admin.to_dict()
    }
    return api_success_response(data)


@bp_admin_api.route('/current_admin/password/', methods=['PUT'])
def update_current_admin_password():
    """
    @apiVersion 1.0.0
    @api {PUT} /api/current_admin/password/ 修改当前管理员密码
    @apiName admin_update_current_admin_password
    @apiGroup admin_Admin
    @apiPermission admin

    @apiParam {String{8..20}} password 密码

    @apiUse e1203
    @apiUse e1204
    @apiUse e1303
    """
    password = g.json.get('password')
    claim_args(1203, password)
    claim_args_str(1204, password)
    claim_args_true(1303, Admin.MIN_PW_LEN <= len(password) <= Admin.MAX_PW_LEN)

    g.admin.set_password(password)
    return api_success_response({})
