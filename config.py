# -*- coding: utf-8 -*-
"""项目配置

数据库连接，flask的相关配置等
"""


class Config:
    # 处于debug模式
    DEBUG = True
    # debug模式
    FLASK_DEBUG = True
    # 序列化不转义非ASCII码
    JSON_AS_ASCII = False
    # cookie/session用到的签名密钥
    SECRET_KEY = 'This_is_secret_key_used_by_session'


# 生产环境配置
class Production(Config):
    DEBUG = False


# 数据库配置
class DBConfig:
    SERVER = '123.60.156.14'
    PORT = 3306
    DATABASE = 'db_music_trans'
    USER = 'music_trans_usr'
    PASSWORD = 'music_trans_pwd_01'


# OSS云存储配置
class OSS:
    AccessKeyId = ''
    AccessKeySecret = ''
    Endpoint = ''
    Bucket = ''