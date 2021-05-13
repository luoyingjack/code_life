from __future__ import annotations
from datetime import datetime
from json import dumps, loads
from os import getenv
from time import time
from typing import Iterable, Optional, Type, TypeVar, Union, List, Generator
from uuid import uuid4

import requests
from flask import current_app, json
from peewee import *
from werkzeug.security import check_password_hash, generate_password_hash

from app.component import component
from utils.redis_util import redis_client
from utils.string_util import nullable_strip, to_str
from .api_utils import APIError
from utils.aes_util import aes_crypto


db = MySQLDatabase(
    getenv('MYSQL_DB') or 'code_life-api',
    user=getenv('MYSQL_USER'),
    password=getenv('MYSQL_PASSWORD'),
    host=getenv('MYSQL_HOST') or '127.0.0.1',
    port=int(getenv('MYSQL_PORT') or 3306),
    charset='utf8mb4'
)
T = TypeVar('T', bound='_BaseModel')


class _JSONCharField(CharField):
    """JSON字段（VARCHAR）"""

    def db_value(self, value):
        if value is not None:
            return dumps(value, ensure_ascii=False, sort_keys=True)

    def python_value(self, value):
        if value is not None:
            return loads(value)


class _JSONTextField(TextField):
    """JSON字段（TEXT）"""

    def db_value(self, value):
        if value is not None:
            return dumps(value, ensure_ascii=False, sort_keys=True)

    def python_value(self, value):
        if value is not None:
            return loads(value)


class _BaseModel(Model):
    """表基类"""

    id = AutoField()  # 主键
    create_time = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])  # 创建时间
    update_time = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')])  # 更新时间

    class Meta:
        database = db
        only_save_dirty = True

    @classmethod
    def get_by_id(cls: Type[T], _id: Union[int, str], code: int=0, message: str=None) -> Optional[T]:
        """根据主键获取

        Args:
            _id: 主键
            code: APIError错误码
            message: APIError错误描述

        Raises:
            APIError
        """
        try:
            return cls.select().where(cls.id == _id).get()
        except cls.DoesNotExist:
            if code:
                raise APIError(code, message)

    @classmethod
    def _excluded_field_names(cls) -> set:
        """转换为dict时排除在外的字段名"""
        return set()

    @classmethod
    def _extra_attr_names(cls) -> set:
        """转换为dict时额外增加的属性名"""
        return set()

    def to_dict(self, *, only: Iterable[str]=None, exclude: Iterable[str]=None, recurse: bool=False,
                max_depth: int=None) -> dict:
        """转换为dict

        Args:
            only: 仅包含在内的字段名列表
            exclude: 排除在外的字段名列表
            recurse: 是否对外键进行递归转换
            max_depth: 递归深度，默认无限制
        """
        only = set(only or [])
        exclude = set(exclude or []) | self._excluded_field_names()
        if max_depth is None:
            max_depth = -1
        if max_depth == 0:
            recurse = False
        data = {}

        # fields
        for field_name, field in self._meta.fields.items():
            if field_name in exclude or (only and field_name not in only):
                continue
            field_data = self.__data__.get(field_name)
            if recurse and isinstance(field, ForeignKeyField):
                if field_data:
                    rel_obj = getattr(self, field_name)
                    field_data = rel_obj.to_dict(recurse=True, max_depth=max_depth - 1)
                else:
                    field_data = None
            data[field_name] = field_data

        # extras
        for attr_name in self._extra_attr_names():
            if attr_name in exclude or (only and attr_name not in only):
                continue
            attr = getattr(self, attr_name)
            data[attr_name] = attr() if callable(attr) else attr
        return data

    def save(self, lock_ut: bool=False, **kwargs) -> int:
        """持久化到数据库

        Args:
            lock_ut: 不改变更新时间
        """
        if lock_ut:
            self._dirty.add('update_time')
        return super().save(**kwargs)


class _UUIDMixin(Model):
    """UUID mixin"""

    uuid = UUIDField(unique=True, default=uuid4)  # UUID

    @classmethod
    def get_by_uuid(cls: Type[T], _uuid: str, code: int=0, message: str=None) -> Optional[T]:
        """根据UUID获取

        Args:
            _uuid: UUID
            code: APIError错误码
            message: APIError错误描述

        Raises:
            APIError
        """
        try:
            return cls.select().where(cls.uuid == _uuid).get()
        except cls.DoesNotExist:
            if code:
                raise APIError(code, message)


class _LoginMixin(Model):
    """登录信息 mixin"""

    last_login_time = DateTimeField(null=True)  # 最近登录时间
    last_login_ip = CharField(max_length=64, default='')  # 最近登录IP

    def login(self, ip: str) -> int:
        """登录"""
        self.last_login_time = datetime.now()
        self.last_login_ip = ip
        return self.save(lock_ut=True)


class _WeightMixin(Model):
    """排序权重 mixin"""

    weight = SmallIntegerField(index=True, default=0)  # 排序权重

    def set_weight(self, weight: int) -> int:
        """设置排序权重"""
        self.weight = weight
        return self.save(lock_ut=True)


class Admin(_BaseModel, _UUIDMixin, _LoginMixin):
    """管理员"""

    TOKEN_HEADER = 'Authorization'  # 身份令牌的请求头字段
    TOKEN_EXPIRES = 7  # 身份令牌的过期时间（天）
    MIN_PW_LEN = 8  # 最小密码长度
    MAX_PW_LEN = 20  # 最大密码长度

    username = CharField(max_length=16, unique=True)  # 用户名
    password = CharField(max_length=128)  # 密码

    @classmethod
    def _excluded_field_names(cls):
        return {'password'}

    @classmethod
    def new(cls, username: str, password: str) -> Admin:
        """创建管理员"""
        return cls.create(
            username=username,
            password=generate_password_hash(password)
        )

    @classmethod
    def get_by_username(cls, username: str) -> Optional[Admin]:
        """根据用户名获取"""
        try:
            return cls.select().where(cls.username == username).get()
        except cls.DoesNotExist:
            pass

    @classmethod
    def get_by_token(cls, token: str) -> Optional[Admin]:
        """根据身份令牌获取"""
        try:
            text = aes_crypto.decrypt(token)
            _uuid, expires = text.split(':')
            expires = int(expires)
        except Exception as e:
            current_app.logger.error(e)
        else:
            if expires > time():
                return cls.get_by_uuid(_uuid)

    def gen_token(self) -> str:
        """生成身份令牌"""
        expires = int(time()) + 86400 * self.TOKEN_EXPIRES
        text = '{0}:{1}'.format(self.uuid, expires)
        return aes_crypto.encrypt(text)

    def check_password(self, password: str) -> bool:
        """核对密码"""
        return check_password_hash(self.password, password)

    def set_password(self, password: str) -> int:
        """设置密码"""
        self.password = generate_password_hash(password)
        return self.save()


class Authorizer(_BaseModel):
    """授权方公众号/小程序"""
    SERVICE_CHOICES = (
        (0, '订阅号/小程序'),
        (1, '由历史老帐号升级后的订阅号'),
        (2, '服务号')
    )
    VERIFY_CHOICES = (
        (-1, '未认证'),
        (0, '微信认证'),
        (1, '新浪微博认证'),
        (2, '腾讯微博认证'),
        (3, '已资质认证通过，还未通过名称认证'),
        (4, '已资质认证通过，还未通过名称认证，但通过了新浪微博认证'),
        (5, '已资质认证通过，还未通过名称认证，但通过了腾讯微博认证')
    )

    appid = CharField(max_length=32, unique=True)  # appid
    refresh_token = CharField()  # 接口调用凭据刷新令牌
    func_info = _JSONCharField()  # 授权给开发者的权限集（list）

    service_type = IntegerField(null=True, choices=SERVICE_CHOICES)  # 公众号类型
    verify_type = IntegerField(null=True, choices=VERIFY_CHOICES)  # 认证类型
    nick_name = CharField(null=True)  # 昵称
    principal_name = CharField(null=True)  # 主体名称
    signature = CharField(null=True)  # 帐号介绍
    head_img = CharField(null=True)  # 头像
    qrcode_url = CharField(null=True)  # 二维码图片URL
    user_name = CharField(null=True)  # 原始ID
    alias = CharField(null=True)  # 微信号
    business_info = _JSONCharField(null=True)  # 功能开通状况（dict）
    mini_program_info = _JSONCharField(null=True)  # 小程序信息（dict）

    authorized = BooleanField(default=True)  # 是否已授权

    class Meta:
        table_name = 'authorizer'

    @classmethod
    def new(cls, appid: str, refresh_token: str, func_info: list) -> Authorizer:
        """创建授权方公众号/小程序"""
        return cls.create(
            appid=appid,
            refresh_token=refresh_token,
            func_info=func_info
        )

    @classmethod
    def get_by_appid(cls, appid: str) -> Optional[Authorizer]:
        """根据appid获取"""
        try:
            return cls.select().where(cls.appid == appid).get()
        except cls.DoesNotExist:
            pass

    def update_auth_info(self, refresh_token: str, func_info: list) -> Optional[int]:
        """更新授权信息"""
        self.refresh_token = refresh_token
        self.func_info = func_info
        self.authorized = True
        return self.save_if_changed()

    def update_base_info(self) -> Optional[int]:
        """更新帐号基本信息"""
        base_info, auth_info = component.get_authorizer_info(self.appid)
        self.func_info = auth_info['func_info']
        self.service_type = base_info['service_type_info']['id']
        self.verify_type = base_info['verify_type_info']['id']
        self.nick_name = nullable_strip(base_info.get('nick_name'))
        self.principal_name = nullable_strip(base_info.get('principal_name'))
        self.signature = nullable_strip(base_info.get('signature'))
        self.head_img = nullable_strip(base_info.get('head_img'))
        self.qrcode_url = nullable_strip(base_info.get('qrcode_url'))
        self.user_name = nullable_strip(base_info.get('user_name'))
        self.alias = nullable_strip(base_info.get('alias'))
        self.business_info = base_info['business_info']
        self.mini_program_info = base_info.get('MiniProgramInfo')
        self.authorized = True
        return self.save_if_changed()

    def unauthorized(self) -> Optional[int]:
        """取消授权"""
        if self.authorized:
            self.authorized = False
            return self.save_ut()

    def get_access_token(self) -> str:
        """获取接口调用凭据"""
        key = 'authorizer:{0}:access_token'.format(self.appid)
        value = redis_client.get(key)
        if value:
            return to_str(value)
        access_token, expires_in = component.get_authorizer_access_token(self.appid, self.refresh_token)
        redis_client.set(key, access_token, ex=int(expires_in) - 300)  # 提前5分钟更新access_token
        return access_token

    def get_jsapi_ticket(self) -> str:
        """获取jsapi_ticket"""
        key = 'authorizer:{0}:jsapi_ticket'.format(self.appid)
        value = redis_client.get(key)
        if value:
            return to_str(value)
        url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket'
        params = {
            'access_token': self.get_access_token(),
            'type': 'jsapi'
        }
        ret = requests.get(url, params=params).json()
        ticket, expires_in = map(ret.get, ['ticket', 'expires_in'])
        if not (ticket and expires_in):
            raise RuntimeError(repr(ret))
        redis_client.set(key, ticket, ex=int(expires_in) - 300)  # 提前5分钟更新ticket
        return ticket

    def get_card_api_ticket(self) -> str:
        """获取微信卡券api_ticket"""
        key = 'authorizer:{0}:card_api_ticket'.format(self.appid)
        value = redis_client.get(key)
        if value:
            return to_str(value)
        url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket'
        params = {
            'access_token': self.get_access_token(),
            'type': 'wx_card'
        }
        ret = requests.get(url, params=params).json()
        ticket, expires_in = map(ret.get, ['ticket', 'expires_in'])
        if not (ticket and expires_in):
            raise RuntimeError(repr(ret))
        redis_client.set(key, ticket, ex=int(expires_in) - 300)  # 提前5分钟更新ticket
        return ticket

    def get_user_openid_with_code(self, code:str) -> str:
        """根据code换取用户的openid，适用于base授权"""
        # 通过code换取网页授权access_token
        url = 'https://api.weixin.qq.com/sns/oauth2/component/access_token'
        params = {
            'appid': self.appid,
            'code': code,
            'grant_type': 'authorization_code',
            'component_appid': component.app_id,
            'component_access_token': component.get_access_token()
        }
        ret = requests.get(url, params=params).json()
        return ret.get('openid')

    def get_user_info_with_code(self, code: str) -> dict:
        """获取微信用户基本信息（网页授权）"""
        # 通过code换取网页授权access_token
        url = 'https://api.weixin.qq.com/sns/oauth2/component/access_token'
        params = {
            'appid': self.appid,
            'code': code,
            'grant_type': 'authorization_code',
            'component_appid': component.app_id,
            'component_access_token': component.get_access_token()
        }
        ret = requests.get(url, params=params).json()
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
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def get_user_info(self, openid: str) -> dict:
        """获取微信用户基本信息"""
        url = 'https://api.weixin.qq.com/cgi-bin/user/info'
        params = {
            'access_token': self.get_access_token(),
            'openid': openid,
            'lang': 'zh_CN'
        }
        resp = requests.get(url, params=params)
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def send_custom_msg(self, openid: str, msg_type: str, msg_data: dict) -> None:
        """发送客服消息"""
        url = 'https://api.weixin.qq.com/cgi-bin/message/custom/send'
        params = {
            'access_token': self.get_access_token()
        }
        body = {
            'touser': openid,
            'msgtype': msg_type,
            msg_type: msg_data
        }
        ret = requests.post(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), params=params).json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))

    def get_temp_image_media(self, media_id: str) -> bytes:
        """获取临时图片素材"""
        url = 'https://api.weixin.qq.com/cgi-bin/media/get'
        params = {
            'access_token': self.get_access_token(),
            'media_id': media_id
        }
        resp = requests.get(url, params=params)
        content_type = resp.headers['Content-Type']
        if content_type.startswith('application/json'):
            raise RuntimeError(repr(resp.json()))
        if not content_type.startswith('image/'):
            raise RuntimeError('Content-Type is {0}'.format(content_type))
        return resp.content

    def get_tags(self) -> List[dict]:
        """获取标签列表

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/tags/get'
        params = {
            'access_token': self.get_access_token()
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret['tags']

    def get_tag_users(self, tag_id: int, next_openid: str=None) -> dict:
        """获取标签下用户列表

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/user/tag/get'
        params = {
            'access_token': self.get_access_token()
        }
        body = {
            'tagid': tag_id,
            'next_openid': next_openid
        }
        resp = requests.post(url, json=body, params=params)
        resp.raise_for_status()
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def iter_tag_users(self, tag_id: int, next_openid: str=None) -> Generator[str, None, None]:
        """标签下用户openid生成器

        Raises:
            requests.HTTPError
            RuntimeError
        """
        while True:
            ret = self.get_tag_users(tag_id, next_openid)
            count, data, next_openid = map(ret.get, ['count', 'data', 'next_openid'])
            if not count:
                break
            for openid in data['openid']:
                yield openid

    def get_subscribers(self, next_openid: str=None) -> dict:
        """获取关注者列表

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/user/get'
        params = {
            'access_token': self.get_access_token(),
            'next_openid': next_openid
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret

    def iter_subscribers(self, next_openid: str=None) -> Generator[str, None, None]:
        """关注者openid生成器

        Raises:
            requests.HTTPError
            RuntimeError
        """
        while True:
            ret = self.get_subscribers(next_openid)
            count, data, next_openid = map(ret.get, ['count', 'data', 'next_openid'])
            if not count:
                break
            for openid in data['openid']:
                yield openid

    def batch_get_user_info(self, openid_list: List[str]) -> List[dict]:
        """批量获取用户基本信息

        Raises:
            requests.HTTPError
            RuntimeError
        """
        url = 'https://api.weixin.qq.com/cgi-bin/user/info/batchget'
        params = {
            'access_token': self.get_access_token()
        }
        body = {
            'user_list': [{'openid': openid, 'lang': 'zh_CN'} for openid in openid_list]
        }
        resp = requests.post(url, json=body, params=params)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        ret = resp.json()
        if ret.get('errcode'):
            raise RuntimeError(repr(ret))
        return ret['user_info_list']


class UserDemo(_BaseModel):
    """用户表"""
    TOKEN_EXPIRES = 30  # 身份令牌的过期时间（天）
    COOKIE_KEY = '_user_demo'  # 身份令牌的Cookie键
    SEX_CHOICES = (
        (0, '未知'),
        (1, '男'),
        (2, '女')
    )
    SUBSCRIBE_CHOICES = (
        (0, '否'),
        (1, '是')
    )

    openid = CharField(max_length=32, unique=True)
    unionid = CharField(null=True)
    sex = IntegerField(choices=SEX_CHOICES)  # 性别
    nickname = CharField(null=True)  # 昵称
    headimgurl = CharField(null=True)  # 头像
    country = CharField(null=True)  # 所在国家
    province = CharField(null=True)  # 所在省份
    city = CharField(null=True)  # 所在城市

    subscribe = IntegerField(choices=SUBSCRIBE_CHOICES)  # 是否关注公众号
    subscribe_time = IntegerField(null=True)  # 关注时间（时间戳）
    subscribe_scene = CharField(null=True)  # 关注渠道来源
    language = CharField(null=True)  # 语言
    remark = CharField(null=True)  # 备注
    tagid_list = _JSONCharField()  # 标签ID列表（list）

    class Meta:
        table_name = 'demo_user'


models = [Admin, Authorizer, UserDemo]
