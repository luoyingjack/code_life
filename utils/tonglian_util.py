from binascii import b2a_hex
from os import getenv
from time import time_ns

import requests
import xmltodict
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from flask import url_for


class TLTService:
    """通联通"""
    URL = 'https://tlt.allinpay.com/aipg/ProcessServlet'  # 生产环境
    TLT_PUB_KEY = 'tlt_rsa_public_key.pem'

    def __init__(self, merchant_id: str, user_name: str, user_pass: str, rsa_private_key: str):
        self.merchant_id = merchant_id
        self.user_name = user_name
        self.user_pass = user_pass
        self.rsa_private_key = rsa_private_key

    def id_ver(self, req_sn: str, name: str, id_no: str) -> dict:
        """国民身份验证"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '220001'),
                'IDVER': {
                    'NAME': name,
                    'IDNO': id_no
                }
            }
        }
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        return xmltodict.parse(resp.text)

    def three_ver(self, req_sn: str, merchant_id: str, submit_time: str, account_no: str, account_name: str, id_no: str,
                 merrem: str) -> dict:
        """三要素身份验证"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '211003'),
                'VALIDR': {
                    'MERCHANT_ID': merchant_id,
                    'SUBMIT_TIME': submit_time,
                    'BANK_CODE': None,
                    'ACCOUNT_TYPE': '00',
                    'ACCOUNT_NO': account_no,
                    'ACCOUNT_NAME': account_name,
                    'ACCOUNT_PROP': '0',
                    'ID_TYPE': '0',
                    'ID': id_no,
                    'MERREM': merrem
                }
            }
        }
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        return xmltodict.parse(resp.text)

    def four_ver(self, req_sn: str, merchant_id: str, submit_time: str, account_no: str, account_name: str, id_no: str,
                 tel: str, merrem: str) -> dict:
        """四要素身份验证"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '211004'),
                'VALIDR': {
                    'MERCHANT_ID': merchant_id,
                    'SUBMIT_TIME': submit_time,
                    'BANK_CODE': None,
                    'ACCOUNT_TYPE': '00',
                    'ACCOUNT_NO': account_no,
                    'ACCOUNT_NAME': account_name,
                    'ACCOUNT_PROP': '0',
                    'ID_TYPE': '0',
                    'ID': id_no,
                    'TEL': tel,
                    'MERREM': merrem
                }
            }
        }
        # print(self._encrypt(msg).decode('GBK'), flush=True)
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        # print(resp.text, flush=True)
        return xmltodict.parse(resp.text)

    def query_pay(self, req_sn: str, merchant_id: str, query_sn: str) -> dict:
        """交易结果查询"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '200004'),
                'QTRANSREQ': {
                    'MERCHANT_ID': merchant_id,
                    'QUERY_SN': query_sn
                }
            }
        }
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        return xmltodict.parse(resp.text)

    def batch_pay(self, req_sn: str, merchant_id: str, submit_time: str, total_item: str, total_sum: str, data: list) -> dict:
        """批量代付"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '100002'),
                'BODY': {
                    'TRANS_SUM': {
                        'BUSINESS_CODE': '09900',
                        'MERCHANT_ID': merchant_id,
                        'SUBMIT_TIME': submit_time,
                        'TOTAL_ITEM': total_item,
                        'TOTAL_SUM': total_sum
                    },
                    'TRANS_DETAILS': {
                        'TRANS_DETAIL': [{
                                'SN': i.get('sn'),
                                'ACCOUNT_TYPE': '00',
                                'ACCOUNT_NO': i.get('account_no'),
                                'ACCOUNT_NAME': i.get('account_name'),
                                'ACCOUNT_PROP': '0',
                                'AMOUNT': i.get('amount'),
                                'CURRENCY': 'CNY',
                                'NOTIFYURL': url_for('bp_admin_ext.tlt_pay_notify', _external=True)
                            }
                            for i in data
                        ]
                    }
                }
            }
        }
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        return xmltodict.parse(resp.text)

    def balance_query(self, req_sn: str, acctno: str):
        """余额查询"""
        msg = {
            'AIPG': {
                'INFO': self._req_info(req_sn, '300000'),
                'ACQUERYREQ': {
                    'ACCTNO': acctno
                }
            }
        }
        resp = requests.post(self.URL, data=self._encrypt(msg), params=self._req_params(req_sn))
        return xmltodict.parse(resp.text)

    def _encrypt(self, msg: dict) -> bytes:
        """加密"""
        xml = xmltodict.unparse(msg, encoding='GBK', pretty=True, indent='')
        target = '<SIGNED_MSG></SIGNED_MSG>'
        text = xml.replace(target, '')
        sign = self._gen_sign(text)
        return xml.replace(target, '<SIGNED_MSG>' + sign + '</SIGNED_MSG>').encode('GBK', errors='ignore')

    def _gen_sign(self, text: str) -> str:
        """生成签名 SHA1withRSA"""
        with open(self.rsa_private_key) as f:
            key = f.read()
            rsa_key = RSA.import_key(key)
            signer = PKCS1_v1_5.new(rsa_key)
            digest = SHA1.new(text.encode('GBK', errors='ignore'))
            sign = signer.sign(digest)
        return b2a_hex(sign).decode()

    def _req_params(self, req_sn: str) -> dict:
        return {
            'MERCHANT_ID': self.merchant_id,
            'REQ_SN': req_sn
        }

    def _req_info(self, req_sn: str, trx_code: str) -> dict:
        return {
            'TRX_CODE': trx_code,
            'VERSION': '05',
            'DATA_TYPE': '2',
            'LEVEL': '5',
            'MERCHANT_ID': self.merchant_id,
            'USER_NAME': self.user_name,
            'USER_PASS': self.user_pass,
            'REQ_SN': req_sn,
            'SIGNED_MSG': ''
        }


tlt_service = TLTService(getenv('TL_MERCHANT_ID'), getenv('TL_USER_NAME'), getenv('TL_USER_PASS'), getenv('TL_PRI_KRY'))


def verification_id(name: str, account: str):
    """验证国民身份"""
    sn = tlt_service.merchant_id + str(time_ns())
    ret = tlt_service.id_ver(sn, name, account)
    return ret


def verification_three(submit_time: str, account_no: str, account_name: str, id_no: str, merrem: str):
    """三要素验证"""
    sn = tlt_service.merchant_id + str(time_ns())
    ret = tlt_service.three_ver(sn, tlt_service.merchant_id, submit_time, account_no, account_name, id_no, merrem)
    print(ret, flush=True)
    return ret


def verification_four(submit_time: str, account_no: str, account_name: str, id_no: str, tel: str, merrem: str):
    """四要素验证"""
    sn = tlt_service.merchant_id + str(time_ns())
    ret = tlt_service.four_ver(sn, tlt_service.merchant_id, submit_time, account_no, account_name, id_no, tel, merrem)
    return ret


def pay_batch(submit_time: str, total_item: str, total_sum: str, _list: list):
    """批量代付"""
    req_sn = tlt_service.merchant_id + str(time_ns())
    ret = tlt_service.batch_pay(req_sn, tlt_service.merchant_id, submit_time, total_item, total_sum, _list)
    return ret


def pay_query(query_sn: str):
    """交易查询"""
    req_sn = tlt_service.merchant_id + str(time_ns())
    ret = tlt_service.query_pay(req_sn, tlt_service.merchant_id, query_sn)
    return ret


def query_balance():
    """余额查询"""
    req_sn = tlt_service.merchant_id + str(time_ns())
    acctno = tlt_service.merchant_id + '000'
    ret = tlt_service.balance_query(req_sn, acctno)
    return ret
