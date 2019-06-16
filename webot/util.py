import random
import string
import threading
import time
from io import BytesIO

import execjs
import progressbar
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as openpyxlImage
from PIL import Image
from imgcat import imgcat

from webot.common import error_log, get_pic
from webot.data import API_conf_path, MSG_TYPES
from webot.log import debug, success, warning
from webot.conf import conf


class Device:
    @staticmethod
    @error_log()
    def create_device_id():
        """
            创建随机设备指纹
        """
        device_id = f"e{str(random.random())[2:17]}"
        debug(f"device_id: {device_id}")
        return device_id

    @staticmethod
    @error_log()
    def create_client_msg_id():
        """
            创建客户端信息指纹
        """
        client_msg_id = int(time.time() * 1e3) + random.randint(1, 1000)
        debug(f"client_msg_id: {client_msg_id}")
        return client_msg_id

    @staticmethod
    @error_log()
    def get_timestamp(reverse=False):
        """
            获取时间戳,支持取反
        """
        timestamp = None
        if not reverse:
            timestamp = int(time.time() * 1e3)
        else:
            timestamp = execjs.eval("~new Date")
        debug(f"timestamp: {timestamp}")
        return timestamp

    @staticmethod
    @error_log()
    def show_qrcode(buffer):
        """
            打印图片
        """

        # def open():
        #     img = Image.open(buffer)
        #     img.show()

        # code_img = threading.Thread(target=open)
        # code_img.start()
        imgcat(Image.open(buffer))

    @error_log()
    def trans_map(contacts, batch_contacts):
        """
            创建名称列表
        """
        choice_name = (
            lambda item: item.get("RemarkName", "").strip()
            if item.get("RemarkName", "").strip()
            else item.get("NickName", "").strip()
        )
        person_map = {
            item["UserName"]: choice_name(item) for item in contacts["MemberList"]
        }
        for _ in batch_contacts["ContactList"]:
            person_map[_["UserName"]] = _["NickName"]
            for _ in _["MemberList"]:
                person_map[_["UserName"]] = _["NickName"]
        return person_map

    @staticmethod
    def filters(types=None, is_me=False, is_group=False):
        """
            消息过滤
        """
        def decorator(func):
            def wrapper(obj, msg, *args, **kwargs):
                nonlocal types
                if not types or not isinstance(types, list):
                    types = []
                if msg["type"] not in types:
                    return
                if is_group:
                    if not "@@" in msg["from"]:
                        return
                if is_me:
                    if not msg["from"] == conf.my_id:
                        return
                return func(obj, msg, *args, **kwargs)

            return wrapper

        return decorator

    @error_log()
    def export_all_contact(contacts, session, person_data):
        """
            导出通讯录
        """
        warning("Contact exporting...")
        wb = Workbook()
        sheet = wb.active
        keys = contacts["MemberList"][0].keys()
        for x, key in enumerate(keys):
            sheet.cell(row=1, column=x + 1, value=key)
        for y, item in progressbar.progressbar(enumerate(contacts["MemberList"])):
            y = y + 2
            for x, key in enumerate(keys):
                x = x + 1
                data = item[key]

                if key != "HeadImgUrl":
                    if key == "MemberList":
                        data = "".join(data)
                    sheet.cell(row=y, column=x, value=data)
                else:
                    picData = get_pic(session, data)
                    if picData:
                        x = x - 1
                        indexCode = string.ascii_uppercase[x]
                        size = (50, 50)
                        sheet.column_dimensions[indexCode].width, sheet.row_dimensions[
                            y
                        ].height = size
                        img = openpyxlImage(BytesIO(picData))
                        img.width, img.height = size
                        sheet.add_image(img, f"{indexCode}{y}")
                    else:
                        sheet.cell(row=y, column=x, value="")
        wb.save(f'{API_conf_path}/{person_data["User"]["NickName"]}_contacts.xlsx')
        success("Complete!")