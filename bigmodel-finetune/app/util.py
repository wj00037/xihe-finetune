import yaml
import uuid
import pytz
import datetime


def read_full_yaml(path):
    """
    以FullLoader模型读取yaml文件
    :param path: config path
    :return: dict
    """
    with open(path, 'r', encoding='utf-8') as f:
        # basic_config = yaml.load(f.read(), Loader=yaml.FullLoader)
        basic_config = yaml.safe_load(f.read())
    return basic_config

def convert_dict_to_yaml(dict_value):
    """
    将dict保存为yaml文件
    :param dict_value:
    :return: 
    """
    return yaml.dump(dict_value, allow_unicode=True)

# def save_dict_to_yaml(dict_value, save_path):
#     """
#     将dict保存为yaml文件
#     :param dict_value:
#     :return: 
#     """
#     with open(save_path, 'w',  encoding='utf-8') as file:
#         file.write(yaml.dump(dict_value, allow_unicode=True))


def convert_mstimestamp(mstimestamp):
    """
    将ms级时间戳转为上海时区的时间(时间格式：%Y-%m-%d %H:%M:%S)
    :param mstimestamp:
    :return:
    """
    tz = pytz.timezone("Asia/Shanghai")
    dt = datetime.datetime.fromtimestamp(mstimestamp / 1000, tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def convert_msruntime(msduration):
    """
    将ms级别时间戳差转为时间格式(%H:%M:%S)
    :param msduration:
    :return:
    """
    time = datetime.timedelta(days=0, seconds=0, microseconds=0,
                              milliseconds=msduration, minutes=0, hours=0, weeks=0)
    return str(time)


def gen_uuid(num=6):
    """
    将ms级别时间戳差转为时间格式(%H:%M:%S)
    :param name: 需要处理的字符串
    :param num: 生成多少位uuid
    :return: string
    """
    return uuid.uuid1().hex[:num]
