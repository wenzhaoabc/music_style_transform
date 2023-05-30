import json
import os.path

import pymysql.cursors
import mido
from flask import request, session, Blueprint
from midiutil import MIDIFile
from pydub import AudioSegment
from midi2audio import FluidSynth
from dbconn import get_db
from utils import ResponseCode, DatetimeEncoder, trans_music_util

trans_blue = Blueprint('trans', __name__)

trans_map = [
    {
        "origin_id": 29,
        "instrument_id": 18,
        "transed_music_url": "https://musicstyle.oss-cn-shanghai.aliyuncs.com/files/45d30e14f05547058c56b5a64ffd7464/violin.wav",
    },
    {
        "origin_id": 29,
        "instrument_id": 19,
        "transed_music_url": "https://musicstyle.oss-cn-shanghai.aliyuncs.com/files/7ef992fbe45d4087a62fe95c36668eb5/flute.wav",
    },
    {
        "origin_id": 29,
        "instrument_id": 20,
        "transed_music_url": "https://musicstyle.oss-cn-shanghai.aliyuncs.com/files/4db4a3d1a4e144428f41deed4ecbad19/trumpet.wav",
    },
    {
        "origin_id": 29,
        "instrument_id": 21,
        "transed_music_url": "https://musicstyle.oss-cn-shanghai.aliyuncs.com/files/bbdb93daa89a45029d8b48db658dac71/Saxophone.wav",
    },
]


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
                    for item in trans_map:
                        if item.get('origin_id') == music.get('id') and item.get('instrument_id') == instrument_id:
                            url = item.get('transed_music_url')
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


def trans_mp3_to_midi(dir_name):
    # load the mp3 file
    file_path = os.path.join(dir_name, "origin.mp3")
    print('trans_mp3_to_midi', file_path)
    audio = AudioSegment.from_file(file_path, format="mp3")
    # convert to mono and set the frame rate to 44100 Hz
    audio = audio.set_channels(1).set_frame_rate(44100)
    # create a MIDI file with one track
    midi = MIDIFile(1)
    # set the tempo to 120 beats per minute
    midi.addTempo(0, 0, 120)
    # iterate over the audio samples and add notes to the MIDI file
    for i, sample in enumerate(audio.get_array_of_samples()):
        velocity = abs(sample) // 256
        pitch = (sample + 32768) // 256
        if velocity > 0:
            midi.addNote(0, 0, pitch, i / audio.frame_rate, i / audio.frame_rate + 0.1, velocity)
    # write the MIDI file to disk
    print(midi)
    with open(os.path.join(dir_name, "origin.mid"), "wb") as midi_file:
        midi.writeFile(midi_file)


def trans_midi_instrument(dir_name, instrument_number):
    new_instrument_number = instrument_number
    mid = mido.midifiles.MidiFile(os.path.join(dir_name, "origin.mid"))
    print("mid = ", mid)
    track_0 = mid.tracks[0]
    for i, msg in enumerate(track_0):
        if msg.type == 'program_change':
            print(msg)
            msg.program = new_instrument_number
    mid.save(os.path.join(dir_name, 'modified_file.mid'))
    print("转换乐曲完成，mid --->  mp3")


def trans_midi_to_mp3(dir_name):
    root_path = os.path.abspath(os.path.dirname(dir_name))
    sound_font_path = os.path.join(root_path, "static/default_sound_font.sf2")
    print("sound_font_path = ", sound_font_path)
    s = FluidSynth(sound_font=sound_font_path)
    midi_file_path = os.path.join(dir_name, 'modified_file.mid')
    wav_file_path = os.path.join(dir_name, 'modified_file.wav')
    print("midi --- > wav ：开始转换")
    print(midi_file_path, wav_file_path)
    s.midi_to_audio(midi_file_path, wav_file_path)


@trans_blue.route('/trans_midi', methods=['POST'])
def trans_mp3_by_midi_to_mp3():
    code = ResponseCode.success
    msg = 'success'

    base_path = os.path.abspath(os.path.dirname(__name__))
    # base_path = os.path.abspath(os.path.dirname(base_path))
    dir_name = os.path.join(base_path, 'temp')
    print('base_path = ', base_path, dir_name)

    mp3_file = request.files.get('mp3')
    instrument_number = request.form.get('instrument', type=int)
    mp3_file.save(os.path.join(dir_name, 'origin.mp3'))
    # try:
    #     trans_mp3_to_midi(dir_name)
    # except Exception as e:
    #     print(type(e))
    #     pass
    trans_midi_instrument(dir_name, instrument_number)
    trans_midi_to_mp3(dir_name)

    result = dict(code=code, data='', msg=msg)
    return json.dumps(result)
