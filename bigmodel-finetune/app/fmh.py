import os
import time
import json
import requests
import fm.fm_sdk as fm

from app.obshandler import OBSHandler, asset
from .util import read_full_yaml, convert_mstimestamp, gen_uuid, convert_dict_to_yaml

# 获取当前文件所在的目录的路径
cur_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BASIC_CONFIG_PATH = os.path.join(cur_path, "conf", "asset.yml")
FINETUNE_CONFIG_PATH = os.path.join(cur_path, "conf", "finetune_basic.yml")
finetune_basic = read_full_yaml(path=FINETUNE_CONFIG_PATH)


class FoundationModelHandler:
    def __init__(self):
        """加载配置信息
        Args:
            config_path (url_string): 注册组件相关配置文件
        """
        basic_config = asset
        finetune_config = finetune_basic
        self.finetune_config = finetune_config
        self.__registry_type = str(basic_config["REGISTRY_TYPE"])
        self.__aicc_ak = basic_config["AK"]
        self.__aicc_sk = basic_config["SK"]
        self.__obs_endpoint = basic_config["OBS_ENDPOINT"]
        self.__encryption_option = basic_config["ENCRYPTION_OPTION"]
        self.__user_name = basic_config["AICC_USER_NAME"]
        self.__domain_name = basic_config["AICC_DOMAIN_NAME"]
        self.__passwd = basic_config["AICC_PASSWD"]
        self.__iam_endpoint = basic_config["IAM_ENDPOINT"]
        self.__endpoint = basic_config["ENDPOINT"]
        self.__finetune_log_endpoint = basic_config["FINETUNE_LOG_ENDPOINT"]

        # 设置默认scenario、foundation_model、app_config用于获取session
        self.scenario_default = finetune_config["scenario"]
        foundation_model_default = finetune_config["foundation_model"]["supported"][0]
        self.app_config_default = os.path.join(finetune_config["foundation_model"][
            foundation_model_default]["model_save_path"], finetune_config["foundation_model"][
            foundation_model_default]["inference"]["app_config_name"])

        # 初始化OBSClient
        self.obs_client = OBSHandler(finetune_config["finetune_bucket"])

    def get_config(self):
        """获取微调基本配置文件
        Returns:
            dict: 配置信息，比如预置的大模型app_config、model_config等信息
        """
        return self.finetune_config

    def registry(self):
        """注册fm组件
        Returns:
            bool: 若注册成功则为True，否则为False
        """
        # registry info需要“ ”拼接成一个字符串
        registry_info = " ".join(
            [self.__registry_type, self.__aicc_ak, self.__aicc_sk, self.__obs_endpoint, self.__encryption_option])
        return fm.registry(registry_info=registry_info)

    def create_finetune_by_user(self, user, task_name, foundation_model, task_type, model_config=None, **parameters):
        """通过用户创建微调任务
        Args:
            user (string): 用户
            task_name (string): 任务名称，比如finetune
            foundation_model (string): 大模型名称，比如opt-caption
            task_type (string): 任务类型，比如finetune
            model_config (string, optional): model_config 对应路径. Defaults to None.
        Returns:
            string: -1 或者 job_id(7200a67f-f042-xxxx-xxxx-e7cedcd10dbd)
        """
        params = {}
        supported_params = self.finetune_config["foundation_model"][foundation_model][task_type]["supported_params"]
        for key, value in parameters.items():
            if key in supported_params:
                params[key] = value
        model_save_path = self.finetune_config["foundation_model"][foundation_model]["model_save_path"]
        app_config_name = self.finetune_config["foundation_model"][foundation_model][task_type]["app_config_name"]
        model_config_name = self.finetune_config["foundation_model"][
            foundation_model][task_type]["model_config_name"]
        app_config = os.path.join(model_save_path, app_config_name)
        if params != {}:
            model_yaml = convert_dict_to_yaml({"params": params})
            # 微调的参数并不是创建的时候拉取的，需要一个微调保存一份
            target_path = os.path.join(
                model_save_path, task_type, user, str(int(time.time())), model_config_name)
            path = target_path.replace(
                "obs://" + self.finetune_config["finetune_bucket"] + "/", "")
            print("model path: ", path)
            self.obs_client.put_content(
                target_path=path, content=model_yaml)
            model_config = target_path
        if model_config is None:
            model_config = os.path.join(model_save_path, model_config_name)

        print(task_name, app_config, model_config)
        return self.create_finetune(task_name, app_config, model_config)

    def create_finetune(self, task_name, app_config, model_config):
        """创建微调任务（fm接口）
        Args:
            task_name (string): 微调名称，自定义
            app_config (string): obs url
            model_config (string): obs url
        Returns:
            string: -1 或者 job_id(7200a67f-f042-xxxx-xxxx-e7cedcd10dbd)
        """
        res = fm.finetune(scenario=self.finetune_config["scenario"], app_config=app_config,
                          job_name=task_name, model_config_path=model_config)
        # 一般为-1表示名字重复，或者资源不够，前者可能性大。若要精准捕获异常，联系微调团队改源码
        if res == -1:
            task_name = "-".join([task_name, gen_uuid(6)])
            res = fm.finetune(scenario=self.finetune_config["scenario"], app_config=app_config,
                              job_name=task_name, model_config_path=model_config)

        # 失败为-1; 成功为job_id，比如c2170961-f3a8-xxxx-xxx-1845943479c3
        # print("res: ", res)
        return res

    def delete_finetune(self, job_id):
        """根据job_id删除微调任务, 注意删除时需要删除相关资源（todo）
        Args:
            job_id (string): 样例：2695527d-d0be-xxxx-xxxx-a006ea13d7e4
        Returns:
            bool: None|False
        """
        return fm.delete(scenario=self.scenario_default, app_config=self.app_config_default, job_id=job_id)

    def terminal_finetune(self, job_id):
        """根据job_id终止微调任务
        Args:
            job_id (string): 
        Returns:
            bool: None|False
        """
        return fm.stop(scenario=self.scenario_default, app_config=self.app_config_default, job_id=job_id)

    def get_parm_value(self, parms, key):
        for parm in parms:
            if parm["name"] == key:
                return parm["value"]
        return None

    def get_finetune_info(self, job_id):
        """获取微调信息
        Args:
            job_id (string): 
        Returns:
            dict|None: 
        """
        item = fm.show(scenario=self.scenario_default,
                       app_config=self.app_config_default, job_id=job_id)
        if item != "":
            created_at = convert_mstimestamp(item["metadata"]["create_time"])
            task_name = item["metadata"]["name"]
            parms = item["algorithm"]["parameters"]
            framework = self.get_parm_value(parms, "backend")
            phase = item["status"]["phase"]
            task_type = self.get_parm_value(parms, "task_type")
            # runtime = convert_msruntime(item["status"]["duration"])
            runtime = item["status"]["duration"]
            engine_name = self.finetune_config["foundation_model"]["engine"]

            return {
                "task_name": task_name,
                "framework": framework,
                "phase": phase,
                "task_type": task_type,
                "runtime": runtime,
                "created_at": created_at,
                "engine_name": engine_name
            }
        # job_id不存在
        return None

    def get_finetune_log(self, job_id):
        """根据job_id获取日志
        Args:
            job_id (string): 
        Returns:
            dict: 
        """
        item = fm.show(scenario=self.scenario_default,
                       app_config=self.app_config_default, job_id=job_id)
        log_path_dir = item["spec"]["log_export_path"]["obs_url"]
        log_path_dir = log_path_dir.replace(
            "/" + self.finetune_config["finetune_bucket"] + "/", "")
        path_list = self.obs_client.get_obj_by_delimeter(log_path_dir)
        log_path = self.obs_client.get_log_by_id(
            path_list=path_list, job_id=job_id)
        if not log_path:
            return None

        return {
            "log_path": log_path,
            "content": self.obs_client.read_file(log_path)
        }

    def get_auth(self):
        '''
        获取token
        '''
        url = self.__iam_endpoint
        # 获取token
        auth = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": self.__user_name,
                            "password": self.__passwd,
                            "domain": {
                                "name": self.__domain_name
                            }
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": self.__endpoint
                    }
                }
            }
        }
        auth = json.dumps(auth)
        res = requests.post(url, data=auth, headers={
                            "Content-Type": "application/json"})
        token = res.headers.get('X-Subject-Token')
        return token

    def get_finetune_log_url(self, job_id):
        """根据job_id获取日志
        Args:
            job_id (string): 
        Returns:
            dict: 
        """
        url = os.path.join(self.__finetune_log_endpoint,
                           f"training-jobs/{job_id}/tasks/worker-0/logs/url")
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Auth-Token": self.get_auth()
        }
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        return None


if __name__ == "__main__":
    fmh = FoundationModelHandler()
    fmh.registry()
    start_time = time.time()

    user = "wesley"
    task_name = "fm-6"
    foundation_model = "opt-caption"
    task_type = "finetune"
    epochs = 5
    start_learning_rate = 0.0001
    end_learning_rate = 0.000001
    print(fmh.create_finetune_by_user(user=user, task_name=task_name, foundation_model=foundation_model, task_type=task_type,
          model_config=None, epochs=epochs, start_learning_rate=start_learning_rate, end_learning_rate=end_learning_rate))

    # print(fmh.create_finetune("fm-3", "opt-caption", "finetune"))
    # 终止job_id
    job_id = "7200a67f-f042-47cd-8bda-e7cedcd10dbd"
    # print(fmh.terminal_finetune(job_id=job_id))
    # # 删除job_id
    # job_id = "xxxxx"
    # print(fmh.delete_finetune(job_id=job_id))
    # job_id = "xxxxx"
    # print(fmh.get_finetune_info(job_id=job_id))
    # job_id = "xxxxx"
    # fmh.get_finetune_log(job_id=job_id)

    end_time = time.time()
    print("operatre time ", end_time - start_time)
