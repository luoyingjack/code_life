from io import BytesIO

from PIL import Image, ImageFont, ImageDraw, ImageOps
import io
import time
import qrcode
import requests
from flask import json, current_app

from utils.service_util import qn_service
from utils.weixin_util import get_access_token


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


def create_code(page, scene):
    """生成小程序码"""
    try:
        access_token = get_access_token()
        data = {
            "scene": scene,
            "width": 430,
            "page": page
        }
        url = 'https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={0}'.format(access_token)
        data = json.dumps(data).encode(encoding='utf-8')
        code_json = requests.post(url, data=data)
        time_now = int(time.time())
        key = "qiulin/wxcode/{0}.jpg".format(time_now)
        wxcode_url = qn_service.upload_data(key, code_json.content)
        return wxcode_url
    except Exception as e:
        current_app.logger.error(e)


def make_code(data):
    """生成二维码"""
    # version是二维码的尺寸，数字大小决定二维码的密度
    # error_correction：是指误差
    # box_size:参数用来控制二维码的每个单元(box)格有多少像素点
    # border: 参数用控制每条边有多少个单元格(默认值是4，这是规格的最小值）
    qr = qrcode.QRCode(version=3,
                       error_correction=qrcode.constants.ERROR_CORRECT_L,
                       box_size=8,
                       border=2,
                       )
    # 添加数据
    qr.add_data(str(data))
    # 生成二维码
    qr.make(fit=True)
    img = qr.make_image()
    # 换成bytes类型
    buf = io.BytesIO()
    img.save(buf)
    # 上传七牛
    time_now = int(time.time())
    key = "qiulin/qrcode/{0}.jpg".format(time_now)
    QRcode_url = qn_service.upload_data(key, buf.getvalue())
    return QRcode_url


# 先将 input image 填充为正方形
def fill_image(image):
    width, height = image.size
    # 选取长和宽中较大值作为新图片的
    new_image_length = width if width > height else height
    # 生成新图片[白底]
    new_image = Image.new(image.mode, (new_image_length, new_image_length), color='white')  # 注意这个函数！
    # 将之前的图粘贴在新图上，居中
    if width > height:  # 原图宽大于高，则填充图片的竖直维度 #(x,y)二元组表示粘贴上图相对下图的起始位置,是个坐标点。
        new_image.paste(image, (0, int((new_image_length - height) / 2)))
    else:
        new_image.paste(image, (int((new_image_length - width) / 2), 0))
    # new_image.show()
    return new_image

# 切割图片
def cut_image(image):
    width, height = image.size
    item_width = int(width / 3)  # 因为朋友圈一行放3张图。
    box_list = []
    # (left, upper, right, lower)
    for i in range(3):
        for j in range(3):
            # print((i*item_width,j*item_width,(i+1)*item_width,(j+1)*item_width))
            box = (j * item_width, i * item_width, (j + 1) * item_width, (i + 1) * item_width)
            box_list.append(box)

    image_list = [image.crop(box) for box in box_list]

    return image_list


# 保存图片
def save_images(image_list):
    index = 1
    for image in image_list:
        image.save('/Users/jack/Desktop/九宫格/' + str(index) + '.png', 'PNG')
        index += 1


if __name__ == '__main__':
    file_path = "风景.jpg"
    image = Image.open(file_path)
    image = fill_image(image)
    image_list = cut_image(image)
    save_images(image_list)


