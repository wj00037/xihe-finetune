#!/usr/bin/env python
import os
import logging

from flask import Flask, abort, request, jsonify, g, url_for, make_response
from flask_httpauth import HTTPTokenAuth
from flask_sqlalchemy import SQLAlchemy
from flask_cors import *
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash

from .fmh import FoundationModelHandler

#获取当前文件所在的目录的路径
cur_path = os.path.dirname(os.path.realpath(__file__))
db_path = os.path.join(cur_path, "db.sqlite")

app = Flask(__name__)
fmh = FoundationModelHandler()

CORS(app, supports_credentials=True)

# initialization
app.config["SECRET_KEY"] = "the quick brown fox jumps over the lazy dog"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

auth = HTTPTokenAuth(scheme="JWT")

# extensions
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expiration=600):
        s = Serializer(app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.id}).decode("ascii")

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data["id"])
        return user


@auth.verify_token
def verify_token(token):
    # Config.SECRET_KEY:内部的私钥，这里写在配置信息里
    user = User.verify_auth_token(token)
    if not user:
        return False
    g.user = user
    return True


# 公共返回值


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({"error": "Bad Request"}), 400)


@app.route("/health", methods=["GET"])
def health_func():
    return jsonify({"health": "true"})


@app.route("/foundation-model/users", methods=["POST"])
def new_user():
    if request.json is None:
        abort(400)
    username = request.json.get("username")
    password = request.json.get("password")
    if username is None or password is None:
        abort(400)  # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)  # existing user
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return (jsonify({"username": user.username}), 201, {
        "Location": url_for("get_user", id=user.id, _external=True)
    })


@app.route("/foundation-model/users/<int:id>")
def get_user(id):
    user = User.query.get(id)
    if not user:
        abort(400)
    return jsonify({"username": user.username})


@app.route("/foundation-model/token", methods=["POST"])
def get_auth_token():
    if request.json is None:
        abort(400)
    username = request.json.get("username")
    password = request.json.get("password")
    if username is None or password is None:
        abort(400)  # missing arguments
    user = User.query.filter_by(username=username).first()
    if not user.verify_password(password):
        return jsonify({"status": "-1", "msg": "用户名或者密码错误"})
    g.user = user
    token = g.user.generate_auth_token(86400)
    print(token)
    return jsonify({
        "status": 200,
        "msg": "获取token成功",
        "token": token,
        "duration": 86400
    })


@app.route("/v1/foundation-model/finetune", methods=["POST"])
@auth.login_required
def create_finetune():
    print("create: ", request.json)
    if not request.json:
        abort(400)
    for key in ["user", "task_name", "foundation_model", "task_type"]:
        if key not in request.json and not isinstance(request.json[key], str):
            abort(400)
    data = request.json
    user = data.get("user")
    task_name = data.get("task_name")
    foundation_model = data.get("foundation_model")
    task_type = data.get("task_type")
    parameters = data.get("parameters", None)
    params = {}
    # name value
    #  "parameters": [{"name": "epochs", "value": "2"}, {"name": "start_learning_rate", "value": "0.001"}, {"name": "end_learning_rate", "value": "0.00001"}]
    if parameters:
        for param in parameters:
            params[param["name"]] = param["value"]
    print("params: ", params)
    res = fmh.create_finetune_by_user(user=user,
                                      task_name=task_name,
                                      foundation_model=foundation_model,
                                      task_type=task_type,
                                      **params)
    print("res: ", res)
    if res == -1:
        return jsonify({"status": -1, "msg": "创建微调任务失败"}), 201
    return jsonify({"status": 201, "msg": "创建微调任务成功", "job_id": res}), 201


@app.route("/v1/foundation-model/finetune/<string:job_id>", methods=["GET"])
@auth.login_required
def get_finetune(job_id):
    print("get: ", job_id)
    res = fmh.get_finetune_info(job_id)
    print("res: ", res)
    if not res:
        return jsonify({"status": -1, "msg": "查询微调详情失败"}), 200
    return jsonify({"status": 200, "msg": "查询微调详情成功", "data": res})


@app.route("/v1/foundation-model/finetune/<string:job_id>", methods=["PUT"])
@auth.login_required
def terminal_finetune(job_id):
    print("terminal: ", job_id)
    res = fmh.terminal_finetune(job_id)
    print("res: ", res)
    if res is False:
        return jsonify({"status": -1, "msg": "终止微调任务失败"}), 200
    return jsonify({"status": 202, "msg": "终止微调任务成功"}), 200


@app.route("/v1/foundation-model/finetune/<string:job_id>", methods=["DELETE"])
@auth.login_required
def delete_finetune(job_id):
    print("delete: ", job_id)
    res = fmh.delete_finetune(job_id)
    print("res: ", res)
    if res is False:
        return jsonify({"status": -1, "msg": "删除微调任务失败"}), 200
    return jsonify({"status": 204, "msg": "删除微调任务成功"}), 200


# @app.route("/v1/foundation-model/finetune/<string:job_id>/log/", methods=["GET"])
# @auth.login_required
# def get_log(job_id):
#     res = fmh.get_finetune_log(job_id)
#     if not res:
#         return jsonify({"status": -1, "msg": "查询微调日志失败, 还未生成日志或者job_id不存在"}), 200
#     return jsonify({"status": 200, "msg": "查询微调日志成功", "data": res})


@app.route("/v1/foundation-model/finetune/<string:job_id>/log/",
           methods=["GET"])
@auth.login_required
def get_log(job_id):
    print("get log: ", job_id)
    res = fmh.get_finetune_log_url(job_id=job_id)
    print("res: ", res)
    if not res:
        return jsonify({
            "status": -1,
            "msg": "查询微调日志失败, 还未生成日志或者job_id不存在"
        }), 200
    return jsonify({
        "status": 200,
        "msg": "查询微调日志成功",
        "obs_url": res["obs_url"]
    })


if not os.path.exists(db_path):
    print("create db")
    db.create_all()
print("Worker【%s】 is Running" % (str(os.getpid())))

# if __name__ == "__main__":

#     # 若ModelArts当前版本不支持配置协议与端口，去除ssl_context参数配置，port需为8080
#     # app.run(host="*.*.*.*", port="**", ssl_context="adhoc")
#     app.run(debug=True)
