from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import md5
from os import getenv
from typing import Union

from Crypto.Cipher import AES

from .string_util import to_bytes, to_str


class AESCrypto:
    """AES加解密"""

    def __init__(self, key_seed: Union[bytes, str]):
        """Initializer

        Args:
            key_seed: 密钥种子，用于生成密钥
        """
        self.key = to_bytes(md5(to_bytes(key_seed)).hexdigest())  # AES-256
        self.mode = AES.MODE_CBC
        self.iv = self.key[:16]
        self.block_size = AES.block_size

    def encrypt(self, text: Union[bytes, str]) -> str:
        """AES加密 & BASE64编码"""
        cipher = AES.new(self.key, self.mode, iv=self.iv)
        text = to_bytes(text)
        pad_len = self.block_size - len(text) % self.block_size
        text += bytes([pad_len] * pad_len)
        cipher_data = cipher.encrypt(text)
        return to_str(urlsafe_b64encode(cipher_data))

    def decrypt(self, data: Union[bytes, str]) -> str:
        """BASE64解码 & AES解密"""
        cipher = AES.new(self.key, self.mode, iv=self.iv)
        cipher_data = urlsafe_b64decode(data)
        text = cipher.decrypt(cipher_data)
        pad_len = text[-1]
        return to_str(text[:-pad_len])


aes_crypto = AESCrypto(getenv('AES_KEY_SEED'))
