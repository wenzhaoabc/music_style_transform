# -*- coding: utf-8 -*-
"""
网络请求API
"""
import json

import pymysql.cursors
from flask import request, session

from api import create_app
from dbconn import get_db
from utils import allow_cors, ResponseCode, verify_phone, upload_image, DatetimeEncoder, response_json, upload_file

app = create_app()
app.after_request(allow_cors)
app.after_request(response_json)


@app.route('/register', methods=['POST'])
def register():
    """
    用户注册，post请求，请求体位于body
    ```json
    {
        "phone": "string, 用户手机号",
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
                        "INSERT INTO db_music_trans.t_user(phone,username,password,avatar) VALUES (%s,%s,%s,%s)",
                        (phone, username, password, avatar))
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


@app.route('/login', methods=['POST'])
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


@app.route('/logout', methods=['POST'])
def user_logout():
    """
    用户退出登录
    :return: data域为空
    """
    session.clear()
    result = dict(code=ResponseCode.success, msg='退出登录成功')
    return json.dumps(result)


@app.route('/remove_account', methods=['DELETE'])
def remove_account():
    """
    账户注销，级联删除数据库中用户的有关信息
    :return: data域为空
    """
    user_id = session.get('user_id')
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


@app.route('/modify_user_info', methods=['PUT'])
def modify_user_info():
    """
    用户修改个人信息,put请求，请求体位于body中，根据需要修改
    ```json
    {
        "username": "string, 用户名",
        "password": "string,用户登录密码",
        "avatar": "string,用户头像，已base64编码"
    }
    ```
    :return: 修改成功返回新的用户个人信息，否则data域为空
    """
    user_id = session.get('user_id')
    body_data = request.get_json()
    username = body_data.get('username', 'User')
    password = body_data.get('password')
    avatar = body_data.get('avatar')
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
            db_conn.commit()
            code = ResponseCode.success
            msg = '修改成功'
            cursor.execute(
                "SELECT id, phone,username,avatar,created FROM db_music_trans.t_user WHERE id = %s", (int(user_id)))
            userInfo = cursor.fetchone()
            session.clear()
            session['user_id'] = userInfo['id']
            session['user_phone'] = userInfo['phone']
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()
    else:
        code = ResponseCode.db_not_found
        msg = '用户未登录'

    result = dict(code=code, data=userInfo, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@app.route('/upload_single_image', methods=['POST'])
def upload_image_test():
    """
    以base64的形式上传图片，对于用户头像的上传可以使用该API，上传文件请使用/upload_files
    :return: data域中为访问图片的URL
    """
    body_data = request.get_json()
    base64_img = body_data.get('image')
    image_url = upload_image(base64_img)
    result = dict(url=image_url)
    return json.dumps(result)


@app.route('/upload_files', methods=['POST'])
def flask_upload_files_by_form():
    """
    上传多个文件，文件存在于form中
    :return: data域中为文件名及访问URL
    """
    code = ResponseCode.success
    msg = ''
    data = []

    try:
        for item in request.files.keys():
            file = request.files.get(item)
            file_url = upload_file(file, file.filename)
            file_dict = dict(file=file.filename, url=file_url, success=True)
            data.append(file_dict)
    except IOError:
        data.pop()
        code = ResponseCode.existed_error
        msg = '存在未上传成功的文件'
    finally:
        result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


if __name__ == '__main__':
    app.run()
