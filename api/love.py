import json

import pymysql.cursors
from flask import request, session, Blueprint

from dbconn import get_db
from utils import ResponseCode, DatetimeEncoder

love_blue = Blueprint('love', __name__)


@love_blue.route('/add_love', methods=['POST'])
def add_my_love():
    """
    用户添加收藏，数据位于body
    {
        "transed_id" : 转换后的乐曲的ID,
        "user_id": 非必须，登陆的情况下不需要该参数
    }
    :return: None
    """
    code = ResponseCode.success
    msg = ''
    data = dict()

    transed_id = request.get_json().get('transed_id')
    user_id = session.get("user_id")
    if user_id is None:
        user_id = request.get_json().get('user_id')
        if user_id is None:
            code = ResponseCode.not_login
            msg = '缺失用户id'

    if transed_id is None:
        code = ResponseCode.param_missing
        msg = '参数缺失'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("INSERT INTO t_user_love(user_id, transed_id) VALUES (%s,%s)",
                           (user_id, transed_id))
            db_conn.commit()
            msg = '收藏成功'
            data = dict(success=True)
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


@love_blue.route('/my_loves', methods=['GET'])
def get_user_loves_list():
    """
    获取用户的所有收藏，用户未登录，测试时加URL参数
        user_id=<user_id>
    :return: data域为收藏列表
    [{
        `id`            int  '转换后的乐曲ID',
        `origin_id`     int   '原乐曲的ID',
        `instrument_id` int   '转换所用的乐器的ID',
        `transed_url`   string  '转换后的乐曲文件存储URL',
        `created`       %Y-%m-%d %H:%M:%S  '转换时间',
        `origin` :  原始乐曲的信息
        {
            `id`          int  '歌曲ID',
            `name`        string '乐曲名',
            `artist`      string  '乐曲作者',
            `genre`       string  '体裁，风格',
            `description` string  '对该乐曲的简洁信息',
            `file_url`    string  '乐曲文件存储URL',
            `created_at`  string '创建时间',
        },
        `instrument`: 转换所用的乐器
        {
            `id`          int  '乐器ID',
            `name`         '乐器名',
            `image`       '图片URL',
            `model`       '乐器3维模型的访问URL',
            `description` '描述',
            `category`    '类别',
        }
    }]
    """
    code = ResponseCode.success
    msg = ''
    data = list()
    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.args.get('user_id')
        if user_id is None:
            code = ResponseCode.not_login
            msg = '缺失用户ID'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT tm.* FROM db_music_trans.t_transed_music tm, t_user_love ul "
                           "WHERE tm.id = ul.transed_id AND ul.user_id = %s;",
                           (user_id))
            data = cursor.fetchall()
            for item in data:
                cursor.execute("SELECT * FROM t_music WHERE id = %s",
                               (item.get('origin_id')))
                origin = cursor.fetchone()
                cursor.execute("SELECT * FROM t_instrument WHERE id = %s",
                               (item.get('instrument_id')))
                instrument = cursor.fetchone()
                item['origin'] = json.dumps(origin, cls=DatetimeEncoder)  # TODO 嵌套转字符串
                item['instrument'] = json.dumps(instrument, cls=DatetimeEncoder)  # TODO 嵌套转字符串
                msg = '查询成功'

        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@love_blue.route('/delete_love', methods=['DELETE'])
def delete_my_love_item():
    """
    删除收藏
    数据位于URL参数中
    ?user_id = <> 用户ID，已登陆的情况下不需要
    &transed_id = <> 转换后的乐曲的ID
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = True

    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.args.get('user_id')
        if user_id is None:
            code = ResponseCode.not_login
            msg = '缺失用户ID'

    transed_id = request.args.get('transed_id')
    if transed_id is None:
        code = ResponseCode.param_missing
        msg = '缺失转换后的乐曲的ID'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("DELETE FROM t_user_love WHERE user_id = %s AND transed_id = %s",
                           (user_id, transed_id))
            db_conn.commit()
            data = True
        except db_conn.Error:
            db_conn.rollback()
            data = False
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


@love_blue.route('/my_history', methods=['GET'])
def get_my_trans_history_list():
    """
    获取用户转换的历史记录
    用户未登录的情况下需要URL参数
    user_id=《》
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = list()

    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.args.get('user_id')
        if user_id is None:
            code = ResponseCode.not_login
            msg = '缺失用户ID'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT tm.* FROM db_music_trans.t_transed_music tm, t_user_history uh "
                           "WHERE tm.id = uh.transed_id AND uh.user_id = %s;",
                           (user_id))
            data = cursor.fetchall()
            if data is not None:
                for item in data:
                    cursor.execute("SELECT * FROM t_music WHERE id = %s",
                                   (item.get('origin_id')))
                    origin = cursor.fetchone()
                    cursor.execute("SELECT * FROM t_instrument WHERE id = %s",
                                   (item.get('instrument_id')))
                    instrument = cursor.fetchone()
                    item['origin'] = json.dumps(origin, cls=DatetimeEncoder)  # TODO 嵌套转字符串
                    item['instrument'] = json.dumps(instrument, cls=DatetimeEncoder)  # TODO 嵌套转字符串
                    msg = '查询成功'
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)
