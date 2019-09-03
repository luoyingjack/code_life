import random
import string
from typing import Union


def to_bytes(bytes_or_str: Union[bytes, str]) -> bytes:
    """将字符串转换为bytes"""
    if isinstance(bytes_or_str, str):
        value = bytes_or_str.encode()
    else:
        value = bytes_or_str
    return value


def to_str(bytes_or_str: Union[bytes, str]) -> str:
    """将字符串转换为str"""
    if isinstance(bytes_or_str, bytes):
        value = bytes_or_str.decode()
    else:
        value = bytes_or_str
    return value


def gen_random_str(length: int, chars: str='uld', *, prefix: str='', suffix: str='') -> str:
    """生成随机字符串

    Args:
        length: 字符串总长度
        chars: 使用的字符种类：'u' - 大写字母，'l' - 小写字母，'d' - 数字
        prefix: 字符串前缀
        suffix: 字符串后缀

    Raises:
        ValueError
    """
    random_part_len = length - len(prefix + suffix)
    if random_part_len < 0:
        raise ValueError('Invalid length')
    if random_part_len == 0:
        return prefix + suffix
    population = ''
    if 'u' in chars:
        population += string.ascii_uppercase
    if 'l' in chars:
        population += string.ascii_lowercase
    if 'd' in chars:
        population += string.digits
    if not population:
        raise ValueError('Invalid chars')
    elements = random.choices(population, k=random_part_len)
    return prefix + ''.join(elements) + suffix
