# -*- coding: utf-8 -*-
"""
网络请求API
"""
import json
# 设置当前路径
import sys

sys.path.insert(0, "D:\\WorkSpace\\Python\\style_transform\\music_style_transform\\")
sys.path.append("/workspace/python/music_style_transform/")

from api import create_app
from utils import allow_cors, response_json

app = create_app()
app.after_request(allow_cors)
app.after_request(response_json)
from user import user_blue
from music import music_blue
from file import file_blue
from feedback import feedback_blue
from love import love_blue
from trans import trans_blue

app.register_blueprint(user_blue)
app.register_blueprint(music_blue)
app.register_blueprint(file_blue)
app.register_blueprint(feedback_blue)
app.register_blueprint(love_blue)
app.register_blueprint(trans_blue)


@app.route('/')
def root_router_view():
    result = dict(code=200, data="欢迎访问浅羽音乐", msg="success")
    return json.dumps(result)


if __name__ == '__main__':
    app.run(port=5000, debug=True, host='0.0.0.0')
