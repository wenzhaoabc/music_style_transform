import json
import random
import time
from datetime import datetime

import pymysql.cursors
from flask import request, session, Blueprint

from dbconn import get_db
from utils import ResponseCode, verify_phone, upload_image, DatetimeEncoder, send_mail, verify_mail

user_blue = Blueprint('user', __name__)


@user_blue.route("/blue")
def get_test_blue():
    result = dict(code=200, data="success", msg="success")
    return json.dumps(result)


@user_blue.route('/register', methods=['POST'])
def register():
    """
    用户注册，post请求，请求体位于body
    ```json
    {
        "phone": "string, 用户手机号",
        "mail": "string 用户邮箱",
        "password": "string,哈希加密后的密码",
        "username": "string,用户昵称",
        "avatar": "base64格式，用户头像图片"
    }
    ```
    :return: data字段 注册成功返回userInfo 其余为空
    """
    # 获取request的body里面的数据
    body_data = request.get_json()
    username = body_data.get('username', 'User')
    phone = body_data.get('phone')
    mail = body_data.get('mail')
    password = body_data.get('password')
    avatar = body_data.get('avatar')
    # 获取数据库连接
    db_conn = get_db()
    # response
    code = ResponseCode.success
    msg = ''
    userInfo = None

    if not phone:
        code = ResponseCode.param_missing
        msg = '缺少手机号'
    elif not verify_phone(phone):
        code = ResponseCode.param_error
        msg = '手机号格式错误'
    elif not password:
        code = ResponseCode.param_missing
        msg = '缺少密码'
    else:
        pass

    if avatar and avatar != '':
        try:
            avatar = upload_image(avatar)
        except RuntimeError:
            avatar = None

    if code is ResponseCode.success:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("SELECT id FROM t_user WHERE phone = %s", (phone))
            result = cursor.fetchone()
            if result:
                code = ResponseCode.existed_error
                msg = '该手机号已注册'
            else:
                try:
                    cursor.execute(
                        "INSERT INTO db_music_trans.t_user(phone,mail,username,password,avatar) VALUES (%s,%s,%s,%s,%s)",
                        (phone, mail, username, password, avatar))
                    db_conn.commit()
                    code = ResponseCode.success
                    msg = '已成功注册'
                    cursor.execute(
                        "SELECT id, phone,username,avatar,created FROM db_music_trans.t_user WHERE phone = %s", (phone))
                    userInfo = cursor.fetchone()
                    session.clear()
                    session['user_id'] = userInfo['id']
                    session['user_phone'] = userInfo['phone']
                except db_conn.IntegrityError:
                    code = ResponseCode.existed_error
                    msg = '该手机号已注册'
        except db_conn.Error:
            pass
        finally:
            # 释放游标
            cursor.close()
    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@user_blue.route('/register_mail', methods=['POST'])
def register_with_mail():
    """
    用户注册，post请求，请求体位于body
    ```json
    {
        "phone": "string, 用户手机号", // 非必须
        "mail": "string 用户邮箱",
        "password": "string,哈希加密后的密码",
        "username": "string,用户昵称",
        "avatar": "base64格式，用户头像图片"
    }
    ```
    :return: data字段 注册成功返回userInfo 其余为空
    """
    # 获取request的body里面的数据
    body_data = request.get_json()
    username = body_data.get('username', 'User')
    phone = body_data.get('phone')
    mail = body_data.get('mail')
    password = body_data.get('password')
    avatar = body_data.get('avatar')
    # 获取数据库连接
    db_conn = get_db()
    # response
    code = ResponseCode.success
    msg = ''
    userInfo = None

    if not mail:
        code = ResponseCode.param_missing
        msg = '缺少邮箱'
    elif not verify_mail(mail):
        code = ResponseCode.param_error
        msg = '邮箱格式错误'
    elif not password:
        code = ResponseCode.param_missing
        msg = '缺少密码'
    else:
        pass

    if avatar and avatar != '':
        try:
            avatar = upload_image(avatar)
        except RuntimeError:
            avatar = None

    if code is ResponseCode.success:
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("SELECT id FROM t_user WHERE mail = %s", (mail))
            result = cursor.fetchone()
            if result:
                code = ResponseCode.existed_error
                msg = '该邮箱已注册'
            else:
                try:
                    cursor.execute(
                        "INSERT INTO db_music_trans.t_user(phone,mail,username,password,avatar) VALUES (%s,%s,%s,%s,%s)",
                        (phone, mail, username, password, avatar))
                    db_conn.commit()
                    code = ResponseCode.success
                    msg = '已成功注册'
                    cursor.execute(
                        "SELECT id, phone,mail,username,avatar,created FROM db_music_trans.t_user WHERE mail = %s",
                        (mail))
                    userInfo = cursor.fetchone()
                    session.clear()
                    session['user_id'] = userInfo['id']
                    session['user_phone'] = userInfo.get('phone')
                    session['user_mail'] = userInfo.get('mail')
                except db_conn.IntegrityError:
                    code = ResponseCode.existed_error
                    msg = '该邮箱已注册'
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库链接错误'
        finally:
            # 释放游标
            cursor.close()
    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@user_blue.route('/login', methods=['POST'])
def user_login():
    """
    用户登录，post请求，请求体位于body
    ```json
    {
        "phone": "string,用户手机号",
        "password": "string,哈希加密后的密码"
    }
    ```
    :return: 登陆成功返回userInfo,其余情况为空
    """
    body_data = request.get_json()
    phone = body_data.get('phone')
    password = body_data.get('password')
    code = ResponseCode.success
    msg = ''
    userInfo = None

    if not phone:
        code = ResponseCode.param_missing
        msg = '缺少手机号'
    elif not verify_phone(phone):
        code = ResponseCode.param_error
        msg = '手机号不合法'
    elif not password:
        code = ResponseCode.param_missing
        msg = '密码错误'
    else:
        pass

    if code is ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(
                "SELECT id, phone,username,avatar,created FROM db_music_trans.t_user WHERE phone = %s AND password = %s",
                (phone, password))
            userInfo = cursor.fetchone()
            if not userInfo:
                code = ResponseCode.db_not_found
                msg = '账号或密码错误'
            else:
                session.clear()
                session['user_id'] = userInfo['id']
                session['user_phone'] = userInfo['phone']
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            # 释放游标
            cursor.close()

    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@user_blue.route('/login_mail', methods=['POST'])
def user_login_with_mail():
    """
    用户登录，post请求，请求体位于body
    ```json
    {
        "mail": "string,用户邮箱",
        "password": "string,哈希加密后的密码"
    }
    ```
    :return: 登陆成功返回userInfo,其余情况为空
    """
    body_data = request.get_json()
    mail = body_data.get('mail')
    password = body_data.get('password')
    code = ResponseCode.success
    msg = ''
    userInfo = None

    if not mail:
        code = ResponseCode.param_missing
        msg = '缺少邮箱'
    elif not verify_mail(mail):
        code = ResponseCode.param_error
        msg = '手机号不合法'
    elif not password:
        code = ResponseCode.param_missing
        msg = '密码错误'
    else:
        pass

    if code is ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(
                "SELECT id, phone,mail,username,avatar,created FROM db_music_trans.t_user "
                "WHERE mail = %s AND password = %s",
                (mail, password))
            userInfo = cursor.fetchone()
            if not userInfo:
                code = ResponseCode.db_not_found
                msg = '账号或密码错误'
            else:
                session.clear()
                session['user_id'] = userInfo['id']
                session['user_phone'] = userInfo.get('phone')
                session['user_mail'] = userInfo.get('mail')
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            # 释放游标
            cursor.close()

    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@user_blue.route('/logout', methods=['POST'])
def user_logout():
    """
    用户退出登录
    :return: data域为空
    """
    session.clear()
    result = dict(code=ResponseCode.success, msg='退出登录成功')
    return json.dumps(result)


@user_blue.route('/remove_account', methods=['DELETE'])
def remove_account():
    """
    账户注销，级联删除数据库中用户的有关信息,user_id位于URL参数中
    ?user_id = <>
    :return: data域为空
    """
    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.args.get('user_id')
    db_conn = get_db()
    cursor = db_conn.cursor()
    code = ResponseCode.success
    msg = ''

    if user_id:
        try:
            cursor.execute("DELETE FROM db_music_trans.t_user WHERE id = %s", (int(user_id)))
            db_conn.commit()
            code = ResponseCode.success
            msg = '账户注销成功'
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '数据库错误'
        finally:
            cursor.close()
    else:
        code = ResponseCode.db_not_found
        msg = '账户不存在'
    result = dict(code=code, msg=msg)

    return json.dumps(result)


user_mail_code = dict()


@user_blue.route('/send_verify_code', methods=['POST'])
def get_mail_verify_code():
    """
    用户修改密码获取邮箱验证码数据位于body
    {
        "mail":邮箱
    }
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = False

    body_data = request.get_json()
    mail_addr = body_data.get('mail', str)
    if mail_addr is None or str(mail_addr).find('@') < 0:
        code = ResponseCode.param_missing
        msg = '邮箱格式错误'

    if code == ResponseCode.success:
        ran = random.Random()
        verify_code = ran.randint(100000, 999999)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = \
            f"""
尊敬的用户你好：
    你的验证码为{verify_code},请勿将验证码泄露于他人，此验证码15分钟内有效。
音乐风格迁移
{current_date}
        """
        try:
            send_mail(mail_addr, '音乐风格迁移验证码', content)
            user_mail_code[mail_addr] = dict(code=verify_code, time=time.time())
            data = dict(code=verify_code)
            msg = '验证码发送成功'
        except Exception:
            code = ResponseCode.existed_error
            msg = '验证码发送失败'
        finally:
            pass
    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


@user_blue.route('/modify_passwd', methods=['POST'])
def user_change_password():
    """
    用户修改密码 body
    {
        "mail": "string 用户邮箱",
        "verify_code": "string 邮箱验证码"
        "password": "新密码"
    }
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = dict()
    body_data = request.get_json()
    mail_addr = body_data.get('mail')
    verify_code = body_data.get('verify_code')
    password = body_data.get('password')

    if mail_addr is None or verify_code is None or password is None:
        code = ResponseCode.param_missing
        msg = '参数缺失'

    user_verify_code_data = user_mail_code.get(mail_addr)
    # print(user_mail_code, mail_addr, verify_code, password)
    if user_verify_code_data is None:
        code = ResponseCode.db_not_found
        msg = '邮箱不正确'
    elif str(user_verify_code_data.get('code')) != str(verify_code):
        code = ResponseCode.param_error
        msg = '验证码不正确'
    elif int(time.time() - user_verify_code_data.get('time')) > 60 * 15:
        code = ResponseCode.param_error
        msg = '验证码已过期'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT * FROM t_user WHERE mail = %s LIMIT 1", (mail_addr))
            current_user = cursor.fetchone()
            if current_user is None:
                code = ResponseCode.db_not_found
                msg = '邮箱不正确'
            else:
                cursor.execute("UPDATE t_user SET password=%s WHERE mail = %s", (password, mail_addr))
                db_conn.commit()
                session.clear()
                session['user_id'] = current_user.get('id')
                session['user_phone'] = current_user.get('phone')
                msg = '修改成功'
                data = True
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


@user_blue.route('/modify_user_info', methods=['PUT'])
def modify_user_info():
    """
    用户修改个人信息,put请求，请求体位于body中，根据需要修改
    ```json
    {
        "user_id": "number,用户ID"
        "username": "string, 用户名",
        "password": "string,用户登录密码",
        "avatar": "string,用户头像，已base64编码"
        "avatar_url": "string,用户头像URL，已通过其它API上传文件后的URL"
    }
    ```
    :return: 修改成功返回新的用户个人信息，否则data域为空
    """
    user_id = session.get('user_id')
    body_data = request.get_json()
    username = body_data.get('username', 'User')
    password = body_data.get('password')
    avatar = body_data.get('avatar')
    avatar_url = body_data.get('avatar_url')
    if user_id is None:
        user_id = body_data.get('user_id')
    code = ResponseCode.success
    msg = ''
    userInfo = None

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    if user_id:
        try:
            if username:
                cursor.execute("UPDATE db_music_trans.t_user SET username = %s WHERE id = %s", (username, int(user_id)))
            if password:
                cursor.execute("UPDATE db_music_trans.t_user SET password = %s WHERE id = %s", (password, int(user_id)))
            if avatar:
                avatar_url = upload_image(avatar)
                cursor.execute("UPDATE db_music_trans.t_user SET avatar = %s WHERE id = %s", (avatar_url, int(user_id)))
            if avatar_url:
                cursor.execute("UPDATE db_music_trans.t_user SET avatar = %s WHERE id = %s", (avatar_url, int(user_id)))
            db_conn.commit()
            code = ResponseCode.success
            msg = '修改成功'
            cursor.execute(
                "SELECT id, phone,mail,username,avatar,created FROM db_music_trans.t_user WHERE id = %s",
                (int(user_id)))
            userInfo = cursor.fetchone()
            session.clear()
            if userInfo is not None:
                session['user_id'] = userInfo.get('id')
                session['user_phone'] = userInfo.get('phone')
            else:
                msg = '用户不存在'
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        except Exception:
            code = ResponseCode.param_error
            msg = '上传头像失败'
        finally:
            cursor.close()
    else:
        code = ResponseCode.db_not_found
        msg = '用户未登录'

    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)
