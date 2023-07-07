import os

from obs import ObsClient
from .util import read_full_yaml

cur_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BASIC_CONFIG_PATH = os.path.join(cur_path, "conf", "asset.yml")
asset = read_full_yaml(path=BASIC_CONFIG_PATH)
AK = asset["AK"]
SK = asset["SK"]
BUCKET_NAME = asset["BUCKET_NAME"]
ENDPOINT = asset["OBS_ENDPOINT"]


class OBSHandler:
    def __init__(self, bucket_name=None, endpoint="obs.cn-central-221.ovaijisuan.com"):
        self.access_key = AK
        self.secret_key = SK
        self.bucket_name = BUCKET_NAME if bucket_name is None else bucket_name
        self.endpoint = ENDPOINT
        self.maxkeys = 1000  # 查询的对象最大个数, 最大为1000
        self.obs_client = ObsClient(
            access_key_id=self.access_key,
            secret_access_key=self.secret_key,
            server=self.endpoint
        )

    def close_obs(self):
        self.obs_client.close()

    def get_obj_by_delimeter(self, source_dir, delimiter="/"):
        """
        以delimiter分组获取文件夹下一层的文件路径
        """
        try:
            if source_dir != "":
                source_dir = "".join([source_dir.rstrip("/"), "/"])

            object_list = []
            flag = True
            index = 1
            marker = ""
            while flag:
                resp_list = self.obs_client.listObjects(self.bucket_name, prefix=source_dir, delimiter=delimiter, marker=marker,
                                                        max_keys=self.maxkeys)
                if resp_list.status < 300:
                    # 文件
                    for content in resp_list.body.contents:
                        filepath = content.key
                        if filepath.endswith("/") is False:
                            print('[file][%s] : key: %s' %
                                  (str(index), filepath))
                            object_list.append(filepath)
                            index += 1
                    # 文件夹
                    # for prefix in resp_list.body.commonPrefixs:
                    #     dirpath = prefix.prefix
                    #     print('[obj][%s] : key: %s' % (str(index), dirpath))
                    #     object_list.append(dirpath)
                    #     index += 1
                    flag = resp_list.body.is_truncated
                    marker = resp_list.body.next_marker
                else:
                    print('errorCode:%s\terrorMessage:%s' %
                          (resp_list.errorCode, resp_list.errorMessage))
                    break
        except:
            import traceback
            print(traceback.format_exc())
        return object_list

    def get_log_by_id(self, path_list, job_id):
        for path in path_list:
            if path.endswith(".log") is True and path.find(job_id) != -1:
                return path
        return None

    def read_file(self, path):
        """
        二进制读取文件
        :param path: 
        :return:
        """
        content = ""
        try:
            resp = self.obs_client.getObject(
                self.bucket_name, path, loadStreamInMemory=True)
            if resp.status < 300:
                buffer = resp.body.buffer
                if buffer:
                    content = bytes.decode(resp.body.buffer, "utf-8")
                else:
                    content = ""
                # 获取对象内容
                return content
            else:
                print("获取失败，失败码: %s\t 失败消息: %s" %
                      (resp.errorCode, resp.errorMessage))
        except:
            import traceback
            print(traceback.format_exc())
        return content

    def put_content(self, target_path, content):
        try:
            resp = self.obs_client.putContent(
                self.bucket_name, target_path, content=content)

            if resp.status < 300:
                return True
            else:
                print('errorCode:', resp.errorCode)
                print('errorMessage:', resp.errorMessage)
        except:
            import traceback
            print(traceback.format_exc())
        return False


if __name__ == "__main__":
    bucket_name = "big-model-finetune"
    obs = OBSHandler(bucket_name=bucket_name)

    import time
    start_time = time.time()

    path = "fm/finetune/omni-perception-pretrainer/logs/"
    print(obs.get_obj_by_delimeter(path))
    # print(obs.getDirList(path))

    end_time = time.time()
    print("operatre time ", end_time - start_time)
    obs.close_obs()
