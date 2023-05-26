import json

import pymysql.cursors
from flask import request, session, Blueprint

from dbconn import get_db
from utils import ResponseCode, DatetimeEncoder, trans_music_util

trans_blue = Blueprint('trans', __name__)


@trans_blue.route('/start_trans', methods=['POST'])
def trans_music():
    """
    转换一首乐曲，数据位于body
    {
        "user_id": 用户ID
        "music_id": 音乐的ID，
        "instrument_id": 要转换成的乐器的ID
    }
    :return: data域包括
    {
        `id`            int unsigned auto_increment comment '转换后的乐曲ID',
        `origin_id`     int unsigned not null comment '原乐曲的ID',
        `instrument_id` int unsigned comment '转换所用的乐器的ID',
        `transed_url`   varchar(255) comment '转换后的乐曲文件存储URL',
    }
    """
    code = ResponseCode.success
    msg = ''
    data = dict()

    music_id = request.get_json().get('music_id')
    instrument_id = request.get_json().get('instrument_id')
    if music_id is None or instrument_id is None:
        code = ResponseCode.param_missing
        msg = '缺少必要参数，音乐ID或乐器ID'

    user_id = session.get('user_id')
    if user_id is None:
        user_id = request.get_json().get('user_id')
        user_id = int(user_id)

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT * FROM db_music_trans.t_music WHERE id=%s", (music_id))
            music = cursor.fetchone()
            if music is None:
                code = ResponseCode.db_not_found
                msg = '未查询到该乐器'
                print(msg)
            else:
                music_url = music.get('file_url')
                # TODO("乐曲转换代码")
                try:
                    url = trans_music_util(music_url, instrument_id)
                except Exception:
                    code = ResponseCode.existed_error
                    msg = '转换失败'
                    print(msg)
                    raise Exception

                cursor.execute("INSERT INTO t_transed_music(origin_id, instrument_id, transed_url) VALUES( %s, %s, %s)",
                               (music_id, instrument_id, url))
                db_conn.commit()
                cursor.execute("SELECT LAST_INSERT_ID() as id from t_transed_music")
                trans_music_id = cursor.fetchone().get("id")
                data = dict(id=trans_music_id, origin_id=music_id, instrument_id=instrument_id, transed_url=url)

                # 用户登录的情况下，添加历史记录
                if user_id is not None:
                    cursor.execute("INSERT INTO t_user_history(user_id, transed_id) VALUES (%s,%s)",
                                   (user_id, trans_music_id))
                    db_conn.commit()

        except (db_conn.Error, Exception):
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            print(msg)
            msg = '数据库连接错误'
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)
