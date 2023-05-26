import json

from flask import Blueprint

user_blue = Blueprint('user', __name__)


@user_blue.route("/blue")
def get_test_blue():
    result = dict(code=200, data="success", msg="success")
    return json.dumps(result)
