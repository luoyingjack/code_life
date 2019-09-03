from . import bp_admin_ext
from ...models import db, models, Admin
from utils.service_util import qn_service


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
