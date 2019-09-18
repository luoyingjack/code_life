import io
import ssl
import urllib.request
import xlsxwriter
from app.models import UserDemo
# 跳过ssl证书验证
context = ssl._create_unverified_context()


def user_data():
    """
    导出excel中插入图片
    :return:
    """
    query = UserDemo.select()
    book = xlsxwriter.Workbook('用户表.xlsx')
    sheet = book.add_worksheet()
    titles = ['昵称', '头像']
    for d in range(len(titles)):
        sheet.write(0, d, titles[d])
    n = 1
    for user in query.order_by(UserDemo.id.asc()):
        info = [user.nickname]
        for d in range(len(info)):
            sheet.write(n, d, info[d])
        # 插入图片
        image_data = io.BytesIO(urllib.request.urlopen(user.headimgurl, context=context).read())
        sheet.insert_image(n, 1, user.nickname, options={'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2})
        n += 1
    book.close()
    return 'success'
