# -*- coding: utf-8 -*-
import base64
import json
import re
import smtplib
import uuid
from datetime import datetime, date
from email.header import Header
from email.mime.text import MIMEText

import oss2

from config import OSS


def allow_cors(response):
    """
    允许跨域
    :param response:response
    :return: header中添加跨域支持
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


def response_json(response):
    """
    返回json格式的数据
    :param response: response
    :return: header中修改了Content-Type
    """
    response.headers['Content-Type'] = 'application/json'
    return response


def verify_phone(phone: str | int) -> bool:
    """
    验证手机号是否合法
    :param phone: 用户注册手机号
    :return: 格式合法的手机号返回true否则为false
    """
    ret = re.match(r"^1[35678]\d{9}$", str(phone))
    if ret:
        return True
    else:
        return False


def verify_mail(mail: str) -> bool:
    """
    正则验证邮箱是否合法
    :param mail:
    :return:
    """
    regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    if re.fullmatch(regex, mail):
        return True
    else:
        return False


def decode_base64(base64_data: str) -> str and bytes | None:
    """
    将base64字符串解码成二进制字节数组
    :param base64_data: base64字符串
    :return: 二进制字节数组
    """
    start_char = base64_data.find(':')
    end_char = base64_data.find(';')
    data_start_index = base64_data.find(',') + 1
    if start_char < 1 or end_char < 1:
        return None
    image_name = (base64_data[start_char + 1:end_char]).replace('/', '.')
    return image_name, base64.b64decode(base64_data[data_start_index:])


def upload_image(image: str | bytes | bytearray, image_name: str = "image.jpg") -> str:
    """
    上传图片到阿里云OSS
    :param image:
    :param image_name: 图片名，默认为image
    :return: 图片的URL
    """
    if type(image) is str:
        image_name, image = decode_base64(image)
    auth = oss2.Auth(OSS.AccessKeyId, OSS.AccessKeySecret)
    bucket = oss2.Bucket(auth=auth, endpoint=OSS.Endpoint, bucket_name=OSS.Bucket)
    key = 'images/' + str(str(uuid.uuid4().hex).replace('-', '') + '/' + image_name)
    bucket.put_object(key=key, data=image)
    image_url = 'https://' + OSS.Bucket + '.' + OSS.Endpoint + '/' + key
    return image_url.replace(' ', '')


def upload_file(file, file_name: str) -> str:
    """
    上传文件到OSS
    :param file: 文件
    :param file_name: 文件名
    :return: 访问文件的URL
    """
    auth = oss2.Auth(OSS.AccessKeyId, OSS.AccessKeySecret)
    bucket = oss2.Bucket(auth=auth, endpoint=OSS.Endpoint, bucket_name=OSS.Bucket)
    key = 'files/' + uuid.uuid4().hex.replace('-', '') + '/' + file_name
    bucket.put_object(key=key, data=file)
    file_url = 'https://' + OSS.Bucket + '.' + OSS.Endpoint + '/' + key
    return file_url


def send_mail(to, subject, content):
    from_addr = "shuaitaozhao2023@163.com"
    password = "LMNOHULMMTRWAEZY"
    smtp_server = "smtp.163.com"
    smtp_port = 465
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header(from_addr, 'utf-8')
    msg['To'] = Header(to, 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    try:
        smtp_obj = smtplib.SMTP_SSL(host=smtp_server, port=smtp_port)
        smtp_obj.login(from_addr, password)
        smtp_obj.sendmail(from_addr, to_addrs=to, msg=msg.as_string())
        smtp_obj.quit()
    except smtplib.SMTPException as e:
        print(e)


def send_feedback_mail(user_id, feedback_type, content):
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = \
        f"""
        音乐风格迁移风格开发人员你好：
            id为{user_id}的用户已提交类型为{feedback_type}的反馈信息，内容如下：
            ****
            {content}
            ****
        请及时处理。
        {current_date}
        """
    send_mail("2050747@tongji.edu.cn", "音乐风格迁移", content)
    send_mail("2052000@tongji.edu.cn", "音乐风格迁移", content)
    send_mail("2053518@tongji.edu.cn", "音乐风格迁移", content)


def trans_music_util(url: str, instrument: str):
    """
    转换乐曲
    :param instrument:
    :param url:
    :return: 转换后的乐曲的URL
    """
    return "https://musicstyle.oss-cn-shanghai.aliyuncs.com/files/777bcd949c9b412e8731e2b5836ee314/百鸟朝凤片段.MP3"


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj: any) -> any:
        """
        重写json构造类，增加对解析时间的支持
        """
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)


class ResponseCode:
    """
    response 状态码
    success 200 请求成功
    success_not_content 204 请求成功，响应数据与缓存中的一致
    param_missing 1001 参数缺失
    param_error 1002 参数解析错误
    db_conn_error 2001 数据库连接错误
    db_not_found 2002 数据库中不存在相应数据
    existed_error 3001 数据已存在于数据库中
    not_login 4001 用户未登录
    """
    success = 200
    success_not_content = 204
    param_missing = 1001
    param_error = 1002
    db_conn_error = 2001
    db_not_found = 2002
    existed_error = 3001
    not_login = 4001
