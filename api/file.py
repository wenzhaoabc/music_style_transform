import json

from flask import request, Blueprint

from utils import ResponseCode, upload_image, upload_file

file_blue = Blueprint('file', __name__)


@file_blue.route('/upload_single_image', methods=['POST'])
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


@file_blue.route('/upload_files', methods=['POST'])
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
            print(item)
    except Exception:
        data.pop()
        code = ResponseCode.existed_error
        msg = '存在未上传成功的文件'
    finally:
        result = dict(code=code, data=data, msg=msg)
    return json.dumps(result)
