import email
from os import getenv

from huey import RedisHuey
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header


huey = RedisHuey(
    utc=False,
    host=getenv('REDIS_HOST') or '127.0.0.1',
    port=int(getenv('REDIS_PORT') or 6379),
    db=int(getenv('REDIS_DB') or 0)
)


@huey.task()  # 发送邮件案例
def send_email(content, name, phone, e_mail):
    """发送邮件"""
    try:
        username = 'metapan@dm.interval.im'  # 发送人邮箱
        password = '13lsnXORVyokNpI'  # 发送密钥
        replyto = ''  # 回复邮件接受人邮箱
        receiver = 'info@tailai.bio'  # 接受者邮箱
        msg = MIMEMultipart('html')
        msg['Subject'] = Header('邮件标题')
        from_header = Header('metapan@dm.interval.im', 'utf-8')  # 来自...
        from_header.append('<{}>'.format(username), 'ascii')
        msg['From'] = from_header
        msg['To'] = receiver
        msg['Reply-to'] = replyto
        msg['Message-id'] = email.utils.make_msgid()
        msg['Date'] = email.utils.formatdate()
        content = "邮件内容：" \
                  "<br>" \
                  "<br>" \
                  "<br>" \
                  "{0}" \
                  "<br>" \
                  "<br>" \
                  "<br>" \
                  "来自：{1}" \
                  "<br>" \
                  "联系电话：{2}" \
                  "<br>" \
                  "邮箱地址：{3}".format(content, name, phone, e_mail)
        html = MIMEText(content, _subtype='html', _charset='UTF-8')
        msg.attach(html)
        try:
            client = smtplib.SMTP()
            client.connect('smtpdm.aliyun.com', 80)
            client.login(username, password)
            client.sendmail(username, receiver, msg.as_string())
            client.quit()
        except Exception as e:
            print('1020', e, flush=True)
    except Exception as e:
        print('1022', e, flush=True)