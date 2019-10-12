# -*- coding: utf-8 -*-
import hashlib
import os
from hashlib import md5
from .string_util import to_bytes, gen_random_str

import time

from flask import current_app, url_for
import requests
import xmltodict

WEIXIN = {
    'app_id': os.getenv('WX_APP_ID'),
    'app_secret': os.getenv('WX_APP_SECRET'),
    'mch_id': os.getenv('WEIXIN_MCH_ID'),
    'pay_key': os.getenv('WEIXIN_PAY_KEY'),
    'cert_path': os.getenv('WEIXIN_CERT_PATH'),
    'key_path': os.getenv('WEIXIN_KEY_PATH')
}


def get_session_key_by_code(code):
    """
    获取用户的session_key
    :param code: 
    :return: 
    """

    # 通过code换取
    wx_url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': WEIXIN['app_id'],
        'secret': WEIXIN['app_secret'],
        'js_code': code,
        'grant_type': 'authorization_code'
    }
    resp_json = requests.get(wx_url, params=params, verify=False).json()
    try:
        openid, session_key, unionid = map(resp_json.get, ('openid', 'session_key', 'unionid'))
    except Exception as e:
        current_app.logger.error(e)
        return None, None, None
    return openid, session_key, unionid


def get_access_token() -> str:
    """获取access_token"""
    url = 'https://console.interval.im/api/wechat_mp/access_token/'
    console_token = md5(to_bytes(WEIXIN['app_secret'])).hexdigest()
    params = {
        'app_id': WEIXIN['app_id'],
        'token': console_token
    }
    ret = requests.get(url, params=params).json()
    access_token = ret['data'].get('access_token')
    if not access_token:
        raise RuntimeError(repr(ret))
    return access_token


def generate_pay_sign(data):
    """
    生成微信签名
    :param data: [dict]
    :return:
    """
    pay_key = WEIXIN['pay_key']
    if not pay_key:
        return

    items = ['%s=%s' % (k, data[k]) for k in sorted(data) if data[k]]
    items.append('key=%s' % pay_key)
    return hashlib.md5('&'.join(items).encode('utf-8')).hexdigest().upper()


_HEADERS = {
    'Content-Type': 'application/xml; charset="utf-8"'
}


def place_order(order):
    """
    微信统一下单并支付
    :param order:
    :return:
    """
    if order.order_result_code == 'SUCCESS':
        return

    wx_url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
    template = 'weixin/pay/unified_order.xml'
    params = order.to_dict(only=('body', 'detail', 'attach', 'out_trade_no', 'total_fee',
                                 'spbill_create_ip', 'trade_type', 'openid'))
    params['notify_url'] = url_for('bp_admin_ext.wx_pay_notify', _external=True)
    params['appid'] = WEIXIN['app_id']
    params['mch_id'] = WEIXIN['mch_id']
    params['nonce_str'] = gen_random_str(16)
    params['sign'] = generate_pay_sign(params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(result), '微信支付签名验证失败'
        order.update_order_result(result)

        appid = WEIXIN['app_id']
        nonceStr = gen_random_str(16)
        prepay_id = order.prepay_id
        timeStamp = int(time.time())
        key = WEIXIN['pay_key']
        wx_str = 'appId={0}&nonceStr={1}&package=prepay_id={2}&signType=MD5&timeStamp={3}&key={4}'.format(appid,
                                                                                                          nonceStr,
                                                                                                          prepay_id,
                                                                                                          timeStamp,
                                                                                                          key)
        paySign = hashlib.md5(wx_str.encode()).hexdigest()
        data = {
            'appId': appid,
            'timeStamp': str(timeStamp),
            'nonceStr': nonceStr,
            'package': 'prepay_id={0}'.format(prepay_id),
            'signType': 'MD5',
            'paySign': str(paySign)
        }
        return data
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)


def apply_for_refund(refund):
    """
    微信支付申请退款
    :param refund:
    :return:
    """
    if refund.refund_status in ['PROCESSING', 'SUCCESS', 'CHANGE']:
        return

    wx_url = 'https://api.mch.weixin.qq.com/secapi/pay/refund'
    data = {
        'xml': {
            'appid': WEIXIN['app_id'],
            'mch_id': WEIXIN['mch_id'],
            'nonce_str': gen_random_str(16),
            'out_trade_no': refund.wx_pay_order.out_trade_no,
            'out_refund_no': refund.out_refund_no,
            'total_fee': refund.wx_pay_order.total_fee,
            'refund_fee': refund.refund_fee,
            'refund_fee_type': refund.refund_fee_type,
            'refund_desc': refund.refund_desc,
            'refund_account': refund.refund_account
        }
    }
    sign = generate_pay_sign(data['xml'])
    data['xml']['sign'] = sign
    xml = xmltodict.unparse(data, full_document=False)
    cert = (WEIXIN['cert_path'], WEIXIN['key_path'])
    resp = requests.post(wx_url, data=xml, headers=_HEADERS, cert=cert)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(result), '微信支付签名验证失败'
        refund.update_refund_result(result)
    except Exception as e:
        print(e, flush=True)
        print(resp.text, flush=True)


def query_order(order):
    """
    微信支付查询订单
    :param order:
    :return:
    """
    wx_url = 'https://api.mch.weixin.qq.com/pay/orderquery'
    template = 'weixin/pay/order_query.xml'
    params = {
        'appid': WEIXIN['app_id'],
        'mch_id': WEIXIN['mch_id'],
        'out_trade_no': order.out_trade_no,
        'nonce_str': gen_random_str(16)
    }
    params['sign'] = generate_pay_sign(params)
    xml = current_app.jinja_env.get_template(template).render(**params)
    resp = requests.post(wx_url, data=xml.encode('utf-8'), headers=_HEADERS)
    resp.encoding = 'utf-8'
    try:
        result = xmltodict.parse(resp.text)['xml']
        sign = result.pop('sign')
        assert sign == generate_pay_sign(result), '微信支付签名验证失败'
        order.update_query_result(result)
    except Exception as e:
        current_app.logger.error(e)
        current_app.logger.info(resp.text)

