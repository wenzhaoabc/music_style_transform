# -*- coding: utf-8 -*-
"""
网络请求API
"""
import json

import pymysql.cursors
from flask import request, session
# 设置当前路径
import sys

sys.path.insert(0, "D:\\WorkSpace\\Python\\style_transform\\music_style_transform\\")
sys.path.append("/workspace")

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


@app.route('/instrument/upload', methods=['POST'])
def upload_single_instrument():
    """
    上传乐器，数据位于form中，需要字段为`name`,`description`,`category`,`image`,
    前三个为文本类型，`image`为file类型

    返回数据中data域形式为
    {"id":"","name":"","image":"图片URL","description":"","category":""}
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = None
    name = ''
    description = ''
    category = ''
    image_url = ''

    try:
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.files['image']
        image_url = upload_file(image, image.filename)
    except KeyError:
        msg = '参数错误或缺失'
        code = ResponseCode.param_error
        pass
    except AttributeError:
        msg = '图片缺失'
        code = ResponseCode.param_missing

    if code is ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(
                "INSERT INTO db_music_trans.t_instrument(`name`,`image`,`description`,`category`) VALUES (%s,%s,%s,%s)",
                (name, image_url, description, category))
            db_conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID() AS id")
            insert_id = cursor.fetchone().get('id')
            data = dict(id=insert_id, name=name, image=image_url, description=description, category=category)
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '连接数据库错误'
            data = {}
            pass
        finally:
            cursor.close()

    msg = 'success'
    result = dict(code=code, msg=msg, data=data)
    return json.dumps(result)


def get_single_instrument_by_id(id):
    """
    获取特定ID的乐器信息，GET请求，参数位于URL中 id=<>
    :return: data域为乐器信息{id,name,description,image,category}
    """
    code = ResponseCode.success
    msg = 'success'
    data = {}

    try:
        id = int(id)
    except Exception:
        code = ResponseCode.param_error
        msg = '参数错误'

    if code is ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT * FROM db_music_trans.t_instrument WHERE id = %s", (id))
            data = cursor.fetchone()
            if data is None:
                code = ResponseCode.db_not_found
                msg = '不存在相应数据'
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, msg=msg, data=data)
    return json.dumps(result)


def search_instruments_by_name(instrument_name=None, instrument_category=None):
    """
    按名字/类别查找相应乐器，GET请求，参数name位于URL中
    :param instrument_category: 类别关键字
    :param instrument_name: 名字关键字
    :return: data域为所有匹配的乐器，数组形式
    """
    code = ResponseCode.success
    msg = ''
    data = []

    if (instrument_name is not None) and (instrument_category is None):
        exec_sql = "SELECT * FROM db_music_trans.t_instrument WHERE LOCATE(%s,`name`)>0"
        query_args = (instrument_name)
    elif instrument_category is not None and (instrument_name is None):
        exec_sql = "SELECT * FROM db_music_trans.t_instrument WHERE LOCATE(%s,`category`)>0"
        query_args = (instrument_category)
    else:
        exec_sql = "SELECT * FROM db_music_trans.t_instrument WHERE LOCATE(%s,`name`)>0 AND LOCATE(%s,`category`)>0"
        query_args = (instrument_name, instrument_category)

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(exec_sql, query_args)
        data = cursor.fetchall()
    except db_conn.Error:
        code = ResponseCode.db_conn_error
        msg = '数据库连接错误'
    finally:
        cursor.close()

    msg = len(data)
    result = dict(code=code, msg=msg, data=data)
    return json.dumps(result)


def get_all_instruments():
    """
    获取所有的乐器
    :return: data域为乐器信息的数组
    """
    code = ResponseCode.success
    msg = 'success'
    data = []
    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM db_music_trans.t_instrument")
        data = cursor.fetchall()
    except db_conn.Error:
        code = ResponseCode.db_conn_error
        msg = '连接数据库错误'
    finally:
        cursor.close()

    msg = len(data)
    result = dict(code=code, msg=msg, data=data)
    return json.dumps(result)


@app.route('/instrument', methods=['GET'])
def get_instruments_by_arges():
    instrument_name = request.args.get('name')
    instrument_id = request.args.get('id')
    instrument_category = request.args.get('category')

    if instrument_name or instrument_category:
        return search_instruments_by_name(instrument_name, instrument_category)
    elif instrument_id:
        return get_single_instrument_by_id(instrument_id)
    else:
        return get_all_instruments()


@app.route('/instrument', methods=['DELETE'])
def delete_single_instrument():
    instrument_id = request.args.get('id')
    code = ResponseCode.success
    msg = 'success'

    if instrument_id is None:
        code = ResponseCode.param_missing
        msg = '缺失乐器ID参数'

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)
    if ResponseCode.success is code:
        try:
            cursor.execute("DELETE FROM db_music_trans.t_instrument WHERE `id` = %s", (instrument_id))
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, msg=msg)
    return json.dumps(result)


if __name__ == '__main__':
    app.run()
