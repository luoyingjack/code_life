from re import fullmatch


def check_mobile(mobile: str) -> bool:
    """检查手机号码格式是否正确"""
    pattern = r'1[3-9]\d{9}'
    match_obj = fullmatch(pattern, mobile)
    return bool(match_obj)


def check_email(email: str) -> bool:
    """检查电子邮箱格式是否正确"""
    pattern = r'\S+@\S+\.\S+'
    match_obj = fullmatch(pattern, email)
    return bool(match_obj)


def check_id_card(id_card: str) -> bool:
    """检查身份证号码格式是否正确"""
    pattern_18 = r'[1-9]\d{5}[12]\d{3}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dxX]'
    pattern_15 = r'[1-9]\d{7}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}'
    if len(id_card) == 18 and fullmatch(pattern_18, id_card):
        value = True
    elif len(id_card) == 15 and fullmatch(pattern_15, id_card):
        value = True
    else:
        value = False
    return value
