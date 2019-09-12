import socket
import struct
from base64 import b64decode, b64encode
from hashlib import sha1
from os import getenv
from time import time
from typing import Optional, Tuple, Union

import requests
import xmltodict
from Crypto.Cipher import AES

from utils.redis_util import redis_client
from utils.string_util import to_bytes, to_str, gen_random_str


class WXOPComponent:
    """微信开放平台第三方平台"""
    def __init__(self, app_id: str, app_secret: str, msg_token: str, msg_key: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.msg_token = msg_token
        self.aes_mode = AES.MODE_CBC
        self.aes_block_size = 32
        self.aes_key = b64decode(msg_key + '=')
        self.aes_iv = self.aes_key[:16]

    def _ticket_key(self) -> str:
        return 'component:{0}:verify_ticket'.format(self.app_id)

    @property
    def verify_ticket(self) -> Optional[str]:
        return to_str(redis_client.get(self._ticket_key()))

    @verify_ticket.setter
    def verify_ticket(self, ticket: str) -> None:
        redis_client.set(self._ticket_key(), ticket)

    def get_access_token(self) -> str:
        """获取接口调用凭据"""
        key = 'component:{0}:access_token'.format(self.app_id)
        value = redis_client.get(key)
        if value:
            return to_str(value)
        url = 'https://api.weixin.qq.com/cgi-bin/component/api_component_token'
        body = {
            'component_appid': self.app_id,
            'component_appsecret': self.app_secret,
            'component_verify_ticket': self.verify_ticket
        }
        ret = requests.post(url, json=body).json()
        access_token, expires_in = map(ret.get, ['component_access_token', 'expires_in'])
        if not (access_token and expires_in):
            raise RuntimeError(repr(ret))
        redis_client.set(key, access_token, ex=int(expires_in) - 300)  # 提前5分钟更新access_token
        return access_token

    def get_pre_auth_code(self) -> str:
        """获取预授权码"""
        url = 'https://api.weixin.qq.com/cgi-bin/component/api_create_preauthcode'
        params = {
            'component_access_token': self.get_access_token()
        }
        body = {
            'component_appid': self.app_id
        }
        ret = requests.post(url, json=body, params=params).json()
        pre_auth_code = ret.get('pre_auth_code')
        if not pre_auth_code:
            raise RuntimeError(repr(ret))
        return pre_auth_code

    def get_authorization_info(self, auth_code: str) -> dict:
        """获取授权方的授权信息"""
        url = 'https://api.weixin.qq.com/cgi-bin/component/api_query_auth'
        params = {
            'component_access_token': self.get_access_token()
        }
        body = {
            'component_appid': self.app_id,
            'authorization_code': auth_code
        }
        ret = requests.post(url, json=body, params=params).json()
        info = ret.get('authorization_info')
        if not info:
            raise RuntimeError(repr(ret))
        return info

    def get_authorizer_info(self, authorizer_appid: str) -> Tuple[dict, dict]:
        """获取授权方的帐号基本信息"""
        url = 'https://api.weixin.qq.com/cgi-bin/component/api_get_authorizer_info'
        params = {
            'component_access_token': self.get_access_token()
        }
        body = {
            'component_appid': self.app_id,
            'authorizer_appid': authorizer_appid
        }
        ret = requests.post(url, json=body, params=params).json()
        base_info, auth_info = map(ret.get, ['authorizer_info', 'authorization_info'])
        if not (base_info and auth_info):
            raise RuntimeError(repr(ret))
        return base_info, auth_info

    def get_authorizer_access_token(self, authorizer_appid: str, refresh_token: str) -> Tuple[str, int]:
        """获取授权方的接口调用凭据"""
        url = 'https://api.weixin.qq.com/cgi-bin/component/api_authorizer_token'
        params = {
            'component_access_token': self.get_access_token()
        }
        body = {
            'component_appid': self.app_id,
            'authorizer_appid': authorizer_appid,
            'authorizer_refresh_token': refresh_token
        }
        ret = requests.post(url, json=body, params=params).json()
        access_token, expires_in = map(ret.get, ['authorizer_access_token', 'expires_in'])
        if not (access_token and expires_in):
            raise RuntimeError(repr(ret))
        return access_token, expires_in

    def _gen_msg_sign(self, encrypted_msg: str, timestamp: str, nonce: str) -> str:
        """生成消息体签名"""
        items = [self.msg_token, encrypted_msg, timestamp, nonce]
        items.sort()
        return sha1(to_bytes(''.join(items))).hexdigest()

    def msg_decrypt(self, xml: Union[bytes, str], timestamp: str, nonce: str, msg_sign: str) -> dict:
        """消息体验证和解密"""
        encrypted_msg = xmltodict.parse(xml)['xml']['Encrypt']
        if msg_sign != self._gen_msg_sign(encrypted_msg, timestamp, nonce):
            raise RuntimeError('消息体签名验证失败')
        cipher = AES.new(self.aes_key, self.aes_mode, iv=self.aes_iv)
        cipher_data = b64decode(encrypted_msg)
        text = cipher.decrypt(cipher_data)
        pad_len = text[-1]
        _, msg_len, content = text[:16], text[16:20], text[20:-pad_len]
        msg_len = socket.ntohl(struct.unpack('I', msg_len)[0])
        msg, app_id = content[:msg_len], content[msg_len:]
        if to_str(app_id) != self.app_id:
            raise RuntimeError('消息体尾部AppId验证失败')
        return xmltodict.parse(msg)['xml']

    def msg_encrypt(self, msg_data: dict) -> str:
        """消息体加密"""
        cipher = AES.new(self.aes_key, self.aes_mode, iv=self.aes_iv)
        msg = to_bytes(xmltodict.unparse(msg_data, full_document=False))
        text = to_bytes(gen_random_str(16)) + struct.pack('I', socket.htonl(len(msg))) + msg + to_bytes(self.app_id)
        pad_len = self.aes_block_size - len(text) % self.aes_block_size
        text += bytes([pad_len] * pad_len)
        cipher_data = cipher.encrypt(text)
        encrypted_msg = to_str(b64encode(cipher_data))
        timestamp = str(int(time()))
        nonce = gen_random_str(16)
        msg_sign = self._gen_msg_sign(encrypted_msg, timestamp, nonce)
        data = {
            'xml': {
                'Encrypt': encrypted_msg,
                'MsgSignature': msg_sign,
                'TimeStamp': timestamp,
                'Nonce': nonce
            }
        }
        return xmltodict.unparse(data, full_document=False)


component = WXOPComponent(getenv('COMPONENT_APP_ID'), getenv('COMPONENT_APP_SECRET'),
                          getenv('COMPONENT_MSG_TOKEN'), getenv('COMPONENT_MSG_KEY'))
