import json

import pymysql.cursors
from flask import request, Blueprint

from dbconn import get_db
from utils import ResponseCode, DatetimeEncoder, upload_file

music_blue = Blueprint('music', __name__)


@music_blue.route('/instrument/upload', methods=['POST'])
def upload_single_instrument():
    """
    上传乐器，数据位于form中，需要字段为`name`,`name_image`,`audio`,`description`,`category`,`image`,
    前三个为文本类型，`image`为file类型

    返回数据中data域形式为
    {"id":"","name":"","image":"图片URL","description":"","category":""}
    :return:
    """
    code = ResponseCode.success
    msg = 'success'
    data = None
    name = ''
    description = ''
    category = ''
    image_url = ''
    model_url = ''
    name_image = ''
    audio = ''

    try:
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.files['image']
        image_url = upload_file(image, image.filename)
        model = request.files.get('model')
        model_url = upload_file(model, model.filename)
        name_image = request.files.get('name_image')
        if name_image is not None:
            name_image = upload_file(name_image, name_image.filename)
        audio = request.files.get('audio')
        if audio is not None:
            audio = upload_file(audio, audio.filename)
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
                "INSERT INTO db_music_trans.t_instrument(`name`,`image`,`model`,`description`,`category`,"
                "`name_image`,`audio`)"
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (name, image_url, model_url, description, category, name_image, audio))
            db_conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID() AS id")
            insert_id = cursor.fetchone().get('id')
            data = dict(id=insert_id, name=name, image=image_url, model=model_url, description=description,
                        category=category, name_image=name_image, audio=audio)
        except db_conn.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = '连接数据库错误'
            data = {}
            pass
        finally:
            cursor.close()

    # msg = 'success'
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

    # msg = len(data)
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


@music_blue.route('/instrument', methods=['GET'])
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


@music_blue.route('/instrument', methods=['DELETE'])
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


@music_blue.route('/music', methods=['POST'])
def post_single_music():
    """
    上传乐曲,所有数据存于form表单中
    name : Text 乐曲名
    artist : Text 作者
    genre : Text 体裁风格
    description : Text 乐曲简介
    file : File 乐曲文件
    instrument : List [{"name":"name:String","weight":weight:float}], 该乐曲演凑的乐曲及其权重
    :return: data域为该乐曲的上传信息
    """
    code = ResponseCode.success
    msg = ''
    mi = dict()
    try:
        mi['name'] = request.form['name']
        mi['artist'] = request.form['artist']
        mi['genre'] = request.form['genre']
        mi['description'] = request.form['description']
        mi['instrument'] = request.form['instrument']
        mi['instrument'] = json.loads(mi['instrument'])

        file = request.files.get('file')
        img = request.files.get('image')
        if (file is None) or (img is None):
            raise FileNotFoundError
        else:
            mi['image'] = upload_file(img, img.filename)
            mi['file'] = upload_file(file, file.filename)
    except FileNotFoundError:
        code = ResponseCode.param_missing
        msg = '缺失乐曲文件'
    except Exception as e:
        print(e)
        code = ResponseCode.param_missing
        msg = '参数缺失'

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(
                "INSERT INTO db_music_trans.t_music(`name`,`cover`,`image`, artist, genre, `description`, file_url)"
                " VALUES "
                "(%s,%s,%s,%s,%s,%s,%s)",
                (mi['name'], mi['image'], mi['image'], mi['artist'], mi['genre'], mi['description'], mi['file']))
            db_conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID() AS id FROM db_music_trans.t_music")
            mi['id'] = cursor.fetchone()['id']
            # 已收录的乐器
            instruments = list()
            for item in list(mi['instrument']):
                cursor.execute("SELECT `id`,`name` FROM db_music_trans.t_instrument WHERE `name` = %s", (item['name']))
                temp = cursor.fetchone()
                if temp is None:
                    msg = "未收录乐器{}".format(item['name'])
                    raise pymysql.err.Warning
                inst_id = temp['id']
                cursor.execute("INSERT INTO db_music_trans.t_music_instrument(music_id, instrument_id, weight) VALUES "
                               "(%s,%s,%s)",
                               (mi['id'], inst_id, item['weight']))

                instruments.append(dict(id=temp['id'], name=temp['name'], weight=item['weight']))
            mi['instrument'] = json.dumps(instruments)  # TODO 嵌套转字符串
            db_conn.commit()
        except pymysql.Error:
            db_conn.rollback()
            code = ResponseCode.db_conn_error
            msg = "数据库链接错误"
        except pymysql.Warning:
            db_conn.rollback()
            code = ResponseCode.db_not_found
        finally:
            cursor.close()

    result = dict(code=code, data=mi, msg=msg)
    return json.dumps(result)


@music_blue.route('/music_inst_type', methods=['GET'])
def get_music_list_by_inst_type():
    """
    获取某一类型乐器演凑的所有曲子
    URL 参数 ?type=<inst_type>
    :return: data域为乐曲列表
    """
    code = ResponseCode.success
    msg = ""
    data = []

    inst_type = request.args.get('type')
    if inst_type is None:
        code = ResponseCode.param_missing
        msg = "缺失URL参数type"

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT t_music.* FROM t_music WHERE id IN "
                           "(SELECT t_mi.music_id AS id FROM t_music_instrument t_mi,t_instrument "
                           "WHERE t_mi.instrument_id=t_instrument.id AND t_instrument.category=%s)",
                           (inst_type))
            data = cursor.fetchall()
            msg = 'success'
        except pymysql.Error:
            code = ResponseCode.db_conn_error
            msg = "数据库连接错误"
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@music_blue.route('/music_id', methods=['GET'])
def get_music_info_by_id():
    """
    URL参数?id=<music_id>
    获取指定id的乐曲的详细信息，包括演凑乐器id等
    :return: data域为乐曲信息
    """
    code = ResponseCode.success
    msg = ''
    data = dict()

    music_id = request.args.get('id')
    if id is None:
        code = ResponseCode.param_missing
        msg = "缺少乐曲ID"

    if code == ResponseCode.success:
        db_conn = get_db()
        cursor = db_conn.cursor(pymysql.cursors.DictCursor)

        try:
            cursor.execute("SELECT t_music.* FROM t_music WHERE id=%s", (music_id))
            data = cursor.fetchone()
            if data is not None:
                cursor.execute("SELECT * FROM t_music_instrument WHERE music_id=%s", (music_id))
                data['instruments'] = json.dumps(cursor.fetchall(), cls=DatetimeEncoder)  # TODO 嵌套转字符串
                msg = 'success'
            else:
                code = ResponseCode.db_not_found
                msg = "数据不存在"
        except pymysql.Error:
            code = ResponseCode.db_conn_error
            msg = "数据库连接错误"
        finally:
            cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@music_blue.route('/music_all', methods=['GET'])
def get_all_music():
    """
    获取所有乐曲
    :return: data域为乐曲列表
    """
    code = ResponseCode.success
    msg = ""
    data = []

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM t_music WHERE id > 23 ORDER BY created_at")
        data = cursor.fetchall()
        msg = 'success'
    except pymysql.Error:
        code = ResponseCode.db_conn_error
        msg = "数据库连接错误"
    finally:
        cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)


@music_blue.route('/music_count', methods=['GET'])
def get_count_music():
    """
    获取所有乐曲
    :return: data域为乐曲列表
    """
    code = ResponseCode.success
    msg = ""
    data = []

    count = request.args.get('count', type=int)
    if not count:
        count = 5

    db_conn = get_db()
    cursor = db_conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute("SELECT * FROM t_music WHERE id > 23 ORDER BY created_at LIMIT %s", (count))
        data = cursor.fetchall()
        msg = 'success'
    except pymysql.Error:
        code = ResponseCode.db_conn_error
        msg = "数据库连接错误"
    finally:
        cursor.close()

    result = dict(code=code, data=data, msg=msg)
    return json.dumps(result, cls=DatetimeEncoder)
