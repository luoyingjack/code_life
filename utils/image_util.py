from io import BytesIO

import requests
from PIL import Image, ImageFont, ImageDraw, ImageOps


def gen_image(head_img: str, back_image: str):
    """图片处理"""
    # 获取头像
    head_res = requests.get(head_img)
    head_image = Image.open(BytesIO(head_res.content))
    head_image = head_image.resize((120, 120))
    # 获取背景图
    back_res = requests.get(back_image)
    back_image = Image.open(BytesIO(back_res.content))
    back_image = back_image.resize((1080, 1920))

    # 合成头像和昵称
    front_size = 12  # 字体大小
    font = ImageFont.truetype('./static/宋体.otf', front_size * 3)
    obj = ImageDraw.Draw(back_image)
    font_color = '#FFFFFF'  # 字体颜色
    # 头像为圆形
    size = (120, 120)
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)

    head_image = ImageOps.fit(head_image, mask.size, centering=(0.5, 0.5))
    head_image.putalpha(mask)

    # 将图片放到背景图上
    back_image.paste(head_image, (48, 48), head_image)
    # 合成昵称
    text = '文字/文字'
    obj.text((48, 84), text, font_color, font=font)
    return 'success'
