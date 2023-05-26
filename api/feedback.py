import json

import pymysql.cursors
from flask import request, session, Blueprint

from dbconn import get_db
from utils import ResponseCode, DatetimeEncoder, send_feedback_mail

feedback_blue = Blueprint('feedback', __name__)


# 用户提交反馈信息
@feedback_blue.route('/feedback', methods=['POST'])
def user_push_feedback():
    """
    用户提交反馈信息，需要登陆后操作，body数据如下
    {
        "user_id": "反馈用户ID，非必须，用户已登录的情况下无需该字段《number》",
        "type": "反馈类型《String》",
        "content": "反馈的内容《String》1000字以内"
    }
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = dict()
    body_data = request.get_json()
    user_id = session.get('user_id')
    if user_id is None:
        user_id = body_data.get('user_id')
    if user_id is None:
        code = ResponseCode.param_missing
        msg = '缺失用户ID'

    feedback_type = body_data.get('type')
    feedback_content = body_data.get('content')

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    if code == ResponseCode.success:
        try:
            cursor.execute("INSERT INTO t_customer_feedback(user_id, type, content) VALUES (%s,%s,%s)",
                           (user_id, feedback_type, feedback_content))
            db_conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID() AS id FROM t_customer_feedback")
            data['id'] = cursor.fetchone().get('id')
            data['type'] = feedback_type
            data['content'] = feedback_content
            data['is_replied'] = False
            send_feedback_mail(user_id, feedback_type, feedback_content)
        except db_conn.Error:
            data = dict()
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '数据库链接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)


# 获取当前用户的所有反馈信息
@feedback_blue.route('/my_feedback', methods=['GET'])
def get_my_feedback_list():
    """
    获取请求用户的所有反馈信息，无参数,
    测试时用户未登录的情况添加URL参数
    user_id=<userId,number>
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
        msg = '用户未登录'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM t_customer_feedback WHERE user_id=%s", (user_id))
            data = cursor.fetchall()
            msg = '查询成功'
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@feedback_blue.route('/all_feedback', methods=['GET'])
def get_all_feedback_list():
    """
    获取所有反馈信息,无参数返回全部
    添加参数is_replied = 1/0获取已回复/未回复的反馈信息，
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = list()

    is_replied = None
    try:
        is_replied = request.args.get('is_replied', type=int)
    except ValueError:
        code = ResponseCode.param_error
        msg = '参数解析错误'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            if is_replied is None:
                cursor.execute("SELECT * FROM t_customer_feedback WHERE TRUE")
                data = cursor.fetchall()
            else:
                is_replied = bool(is_replied)
                cursor.execute("SELECT * FROM t_customer_feedback WHERE is_replied=%s", is_replied)
                data = cursor.fetchall()
            msg = '查询成功'
        except db_conn.Error:
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@feedback_blue.route('/reply_feedback', methods=['POST'])
def reply_one_feedback():
    """
    回复一个反馈信息 请求数据位于body格式如下
    {
        "id": "该反馈的唯一标识符id，必须",
        "reply": "回复内容，1000字以内"
    }
    :return:
    """
    code = ResponseCode.success
    msg = ''
    data = list()
    body_data = request.get_json()

    feedback_id = body_data.get('id')
    reply = body_data.get('reply')

    if feedback_id is None:
        code = ResponseCode.param_error
        msg = '缺少反馈ID'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("UPDATE t_customer_feedback SET is_replied=TRUE,reply=%s,reply_time=CURRENT_TIMESTAMP() "
                           "WHERE id=%s", (reply, feedback_id))
            db_conn.commit()
            msg = '回复成功'
            cursor.execute("SELECT * FROM t_customer_feedback WHERE id=%s", (feedback_id))
            data = cursor.fetchone()
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)
