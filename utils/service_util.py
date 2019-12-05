from hashlib import md5
from json import dumps
from os import getenv
from typing import BinaryIO, Iterable, Optional, Union

import requests
from qiniu import Auth, put_data, put_file
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest

from .string_util import to_bytes


class QNService:
    """七牛"""

    def __init__(self, access_key: str, secret_key: str, bucket: str, domain: str):
        self.auth = Auth(access_key, secret_key)
        self.bucket = bucket
        self.domain = domain

    def gen_upload_token(self, **kwargs) -> str:
        """生成上传凭证"""
        return self.auth.upload_token(self.bucket, **kwargs)

    def upload_data(self, key: str, data: Union[bytes, BinaryIO]) -> Optional[str]:
        """上传二进制流，上传成功则返回URL

        Args:
            key: 上传的文件名
            data: 上传的二进制流
        """
        up_token = self.gen_upload_token(key=key)
        ret, _ = put_data(up_token, key, data)
        if ret and ret.get('key') == key:
            url = 'https://{0}/{1}'.format(self.domain, key)
            return url

    def upload_file(self, key: str, file_path: str) -> Optional[str]:
        """上传文件，上传成功则返回URL

        Args:
            key: 上传的文件名
            file_path: 上传文件的路径
        """
        up_token = self.gen_upload_token(key=key)
        ret, _ = put_file(up_token, key, file_path)
        if ret and ret.get('key') == key:
            url = 'https://{0}/{1}'.format(self.domain, key)
            return url


class YPService:
    """云片"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def single_send(self, mobile: str, text: str) -> dict:
        """单条发送，返回云片响应数据

        Args:
            mobile: 手机号码
            text: 短信内容

        Raises:
            requests.HTTPError
        """
        body = {
            'apikey': self.api_key,
            'mobile': mobile,
            'text': text
        }
        resp = requests.post('https://sms.yunpian.com/v2/sms/single_send.json', data=body)
        resp.raise_for_status()
        return resp.json()

    def batch_send(self, mobiles: Iterable[str], text: str) -> dict:
        """批量发送，返回云片响应数据

        Args:
            mobiles: 手机号码列表
            text: 短信内容

        Raises:
            requests.HTTPError
        """
        body = {
            'apikey': self.api_key,
            'mobile': ','.join(mobiles),
            'text': text
        }
        resp = requests.post('https://sms.yunpian.com/v2/sms/batch_send.json', data=body)
        resp.raise_for_status()
        return resp.json()


class WXMPService:
    """微信公众平台"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.console_token = md5(to_bytes(app_secret)).hexdigest()

    def get_access_token(self) -> str:
        """获取access_token

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://console.interval.im/api/wechat_mp/access_token/'
        params = {
            'app_id': self.app_id,
            'token': self.console_token
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        ret = resp.json()
        access_token = ret['data'].get('access_token')
        if not access_token:
            raise RuntimeError(repr(ret))
        return access_token

    def get_jsapi_ticket(self) -> str:
        """获取jsapi_ticket

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://console.interval.im/api/wechat_mp/jsapi_ticket/'
        params = {
            'app_id': self.app_id,
            'token': self.console_token
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        ret = resp.json()
        ticket = ret['data'].get('jsapi_ticket')
        if not ticket:
            raise RuntimeError(repr(ret))
        return ticket

    def get_user_info(self, openid: str) -> dict:
        """获取微信用户基本信息

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/user/info'
        params = {
            'access_token': self.get_access_token(),
            'openid': openid,
            'lang': 'zh_CN'
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def get_user_info_with_code(self, code: str) -> dict:
        """获取微信用户基本信息（网页授权）

        Raises:
            requests.HTTPError
            RuntimeError
        """
        # 通过code换取网页授权access_token
        url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
        params = {
            'appid': self.app_id,
            'secret': self.app_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        ret = resp.json()
        access_token, openid = map(ret.get, ['access_token', 'openid'])
        if not (access_token and openid):
            raise RuntimeError(repr(ret))

        # 拉取用户信息
        url = 'https://api.weixin.qq.com/sns/userinfo'
        params = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN'
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def send_custom_msg(self, openid: str, msg_type: str, msg_data: dict) -> None:
        """发送客服消息

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/message/custom/send'
        params = {
            'access_token': self.get_access_token()
        }
        body = {
            'touser': openid,
            'msgtype': msg_type,
            msg_type: msg_data
        }
        resp = requests.post(url, data=to_bytes(dumps(body, ensure_ascii=False)), params=params)
        resp.raise_for_status()
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))


class AliyunSmsService:
    """阿里云短信平台"""
    def __init__(self, access_key, access_secret):
        self.acs_client = AcsClient(access_key, access_secret, 'cn-beijing')
        region_provider.add_endpoint('Dysmsapi', 'cn-beijing', 'dysmsapi.aliyuncs.com')

    def send_sms(self, business_id, phone_numbers, sign_name, template_code, template_param=None):
        sms_request = SendSmsRequest.SendSmsRequest()
        sms_request.set_TemplateCode(template_code)
        if template_param is not None:
            sms_request.set_TemplateParam(template_param)
        sms_request.set_OutId(business_id)
        sms_request.set_SignName(sign_name)
        sms_request.set_PhoneNumbers(phone_numbers)
        sms_response = self.acs_client.do_action_with_exception(sms_request)
        return sms_response


qn_service = QNService(getenv('QN_ACCESS_KEY'), getenv('QN_SECRET_KEY'), getenv('QN_BUCKET'), getenv('QN_DOMAIN'))
yp_service = YPService(getenv('YP_API_KEY'))
wx_mp_service = WXMPService(getenv('WX_MP_APP_ID'), getenv('WX_MP_APP_SECRET'))
aliyun_sms_service = AliyunSmsService(getenv('ALI_SMS_KEY'), getenv('ALI_SMS_SECRET'))

