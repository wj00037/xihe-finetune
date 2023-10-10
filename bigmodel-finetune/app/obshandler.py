import os

from obs import ObsClient


class OBSHandler:
    def __init__(self, basic_config, bucket_name=None, endpoint="obs.cn-central-221.ovaijisuan.com"):
        self.access_key = basic_config["AK"]
        self.secret_key = basic_config["SK"]
        self.bucket_name = basic_config["BUCKET_NAME"] if bucket_name is None else bucket_name
        self.endpoint = basic_config["OBS_ENDPOINT"]
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
