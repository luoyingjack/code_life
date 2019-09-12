from . import bp_admin_ext, appid
from ...models import db, models, Admin, Authorizer, UserDemo
from utils.service_util import qn_service
from urllib.parse import quote_plus
from flask import current_app, make_response, redirect, request, url_for
from ...component import component


@bp_admin_ext.route('/data/init/', methods=['GET'])
def data_init():
    """数据初始化"""
    db.create_tables(models)
    if Admin.select().count() == 0:
        Admin.new('admin', 'interval')
    return 'Success'


@bp_admin_ext.route('/qn/upload_token/', methods=['GET'])
def get_qn_upload_token():
    """
    @apiVersion 1.0.0
    @api {GET} /ext/qn/upload_token/ 获取七牛上传凭证
    @apiName admin_get_qn_upload_token
    @apiGroup admin_Ext

    @apiSuccessExample {json} Success Response
        HTTP/1.1 200 OK
        {
            "uptoken": "xxxxxxxx"
        }
    """
    return {
        'uptoken': qn_service.gen_upload_token()
    }


@bp_admin_ext.route('/wx/user/authorize/', methods=['GET'])
def wx_user_authorize():
    state = request.args.get('state')
    state = quote_plus(state or '/')[:128]
    redirect_uri = quote_plus(url_for('.demo_wx_user_login', _external=True))
    url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid={0}&redirect_uri={1}&response_type=code' \
          '&scope=snsapi_userinfo&state={2}&component_appid={3}#wechat_redirect'.format(appid, redirect_uri, state,
                                                                                        component.app_id)
    return redirect(url)


@bp_admin_ext.route('/demo/wx/user/login/', methods=['GET'])
def demo_wx_user_login():
    """（由微信跳转）微信网页授权：获取微信用户基本信息，登录并跳转"""
    code, state, _appid = map(request.args.get, ['code', 'state', 'appid'])
    resp = make_response(redirect(state or '/'))
    try:
        assert code, '微信网页授权：没有code'
        assert _appid == appid, '微信网页授权：appid校验失败'
        authorizer = Authorizer.get_by_appid(appid)
        info = authorizer.get_user_info_with_code(code)
        full_info = authorizer.get_user_info(info['openid'])
        if full_info.get('subscribe') == 1:
            info = full_info
        else:
            info['subscribe'] = 0
        user = UserDemo.get_by_openid(info['openid'])
        if user:
            user.update_info(**info)
        else:
            user = UserDemo.new(**info)
        if state:
            resp = make_response(redirect('{}?auth'.format(state)))
        resp.set_cookie(UserDemo.COOKIE_KEY, value=user.gen_token(), max_age=86400 * UserDemo.TOKEN_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
    return resp
