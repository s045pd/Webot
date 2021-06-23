import contextlib
import hashlib
import json
import pathlib
import sys
import threading
import time
from dataclasses import dataclass
from io import BytesIO

import execjs
import filetype
import requests
import requests_html
from imgcat import imgcat
from PIL import Image
from retry import retry
from urlextract import URLExtract

from webot.common import (
    addfailed,
    addsucess,
    check_path,
    check_times,
    error_log,
    format_sunburst_city,
    get_pic,
    init_path,
)
from webot.conf import conf
from webot.data import *
from webot.exporter import create_json, load_worker, save_file, save_worker
from webot.log import debug, error, info, success, warning
from webot.parser import Parser
from webot.util import Device

with contextlib.redirect_stdout(None):
    import pygame


@dataclass
class Webot:
    __session = requests_html.HTMLSession()
    __session.headers = conf.fakeHeader
    __session.cookies = requests_html.requests.utils.cookiejar_from_dict(
        {
            "MM_WX_NOTIFY_STATE": "1",
            "MM_WX_SOUND_STATE": "1",
            "mm_lang": "zh_CN",
            "login_frequency": "1",
        }
    )
    __thread_pool = {}  # 任务池
    __voice_pool = []  # 语音池
    __is_online = True  # 初始化上线
    __appid = "wx782c26e4c19acffb"  # appID
    __encoding = None  # 默认编码格式

    __qr_code_uuid = None  # 二维码UUID
    __qr_code_img = None  # 二维码图片
    __device_id = Device.create_device_id()

    __batch_contacts = {}  # 群组信息
    __person_map = {}  # 通讯录转换结果

    __msg_id = None  # 消息id
    __hot_reload = None  # 热启动参数

    def get(self, url, *args, **kargs):
        resp = self.__session.get(url, *args, **kargs)
        if not resp.status_code == 200 and resp.content:
            raise AssertionError()
        resp.encoding = "utf8"
        return resp

    def post(self, url, *args, **kargs):
        resp = self.__session.post(url, *args, **kargs)
        if not resp.status_code == 200 and resp.content:
            raise AssertionError()
        resp.encoding = "utf8"
        return resp

    @error_log(raise_exit=True)
    def get_qrcode_uid(self):
        """
        获取二维码ID
        """
        resp = self.get(API_jsLogin)
        self.__qr_code_uuid = Parser.get_qr_code_uuid(resp)
        self.__encoding = Parser.get_encoding(resp)

    @error_log()
    def show_qrcode_local(self, buffer):
        with pathlib.Path(API_qrcode_name).open("wb") as image:
            image.write(buffer)

        self.__qr_code_img = Image.open(API_qrcode_name)
        self.__qr_code_img.show()

    @error_log(raise_exit=True)
    def get_qrcode_img(self):
        """
        获取二维码
        """
        resp = self.get(f"{API_qrcode}{self.__qr_code_uuid}")
        Device.show_qrcode(resp.content, self.show_qrcode_local)

    @error_log()
    def get_base_request(self):
        """
        获取基础请求信息
        """
        base_request = {
            "BaseRequest": {
                "Uin": self.__auth_data["wxuin"],
                "Sid": self.__auth_data["wxsid"],
                "Skey": self.__auth_data["skey"],
                "DeviceID": Device.create_device_id(),
            }
        }
        return base_request

    @error_log()
    def create_synckey(self):
        """
        组合生成synckey
        """
        synckey = "|".join(
            [
                f"{item['Key']}_{item['Val']}"
                for item in self.__person_data["SyncKey"]["List"]
            ]
        )
        debug(f"Synkey:[{synckey}]")
        return synckey

    @retry()
    @error_log(raise_err=True)
    def login_wait(self, local=None):
        """
        登录过程
        """
        return self.get(
            API_login if local else API_check_login,
            params={
                "loginicon": "true",
                "uuid": self.__qr_code_uuid,
                "tip": 1 if local else 0,
                "r": Device.get_timestamp(True),
                "_": Device.get_timestamp(),
            },
            timeout=API_checktimeout,
        )

    @error_log(raise_err=True)
    def login_push_wait(self):
        """
        短时热启动
        """
        self.__session.cookies.update(
            requests_html.requests.utils.cookiejar_from_dict({"login_frequency": "2"})
        )
        resp = self.get(
            API_webwxpushloginurl, params={"uin": self.__session.cookies.get("wxuin")}
        )
        self.__qr_code_uuid = resp.json()["uuid"]
        info(f"New UUID: [{self.__qr_code_uuid}]")
        return True

    def login_localwait(self):
        """
        等待本地终端扫描
        """
        warning("Waiting for app scan")
        self.login_wait(True)
        if self.__qr_code_img:
            self.__qr_code_img.fp.close()

    @error_log(raise_err=True)
    def login_appwait(self, get_ticket=True):
        """
        等待本地终端确认
        """
        warning("Waiting for app confirm")
        resp = self.login_wait(False)
        if get_ticket:
            success("Login Success")
            self.__get_ticket_url = Parser.get_get_ticket_url(resp)

    @error_log()
    def get_ticket(self):
        """
        获取个人信息票据并更新部分cookie
        """
        info(f"Redirect to --> {self.__get_ticket_url}")
        resp = self.get(
            self.__get_ticket_url,
            params={"fun": "new", "lang": "zh_CN", "_": Device.get_timestamp()},
        )
        info(
            f"Get Ticket:{requests_html.requests.utils.dict_from_cookiejar(resp.cookies)}"
        )
        self.__auth_data = Parser.get_auth_data(resp)
        self.__session.cookies.update(
            requests_html.requests.utils.cookiejar_from_dict(
                {"last_wxuin": self.__auth_data["wxuin"]}
            )
        )
        if list(filter(lambda item: item[1], self.__auth_data.items())):
            return True

    def login(self):
        """
        获取认证数据
        """
        if self.__hot_reload and check_path(API_hotreload_file):
            try:
                (
                    self.__session,
                    self.__auth_data,
                    self.__person_data,
                    self.__get_ticket_url,
                ) = load_worker(API_hotreload_file)
                # self.login_push_wait()
                # self.login_appwait(False)
            except Exception:
                error("Hot reload timeout!")
                self.__hot_reload = False
                self.login()
        else:
            self.get_qrcode_uid()
            self.get_qrcode_img()
            self.login_localwait()
            self.login_appwait()

    @error_log()
    def login_success_init(self):
        """
        成功登陆并初始化wx
        """
        resp = self.post(
            API_webwxinit,
            params={"pass_ticket": self.__auth_data["pass_ticket"], "lang": "zh_CN"},
            json=self.get_base_request(),
        )
        resp.encoding = "utf8"
        self.__person_data = resp.json()
        self.__nick = self.__person_data["User"]["NickName"]
        conf.my_id = self.__person_data["User"]["UserName"]
        create_json(self.__person_data, API_static_path / "person_data.json")
        success(
            f"{'Welcome'.center(20,'*')}: [{self.__person_data['User']['NickName']}]"
        )
        save_worker(
            (
                self.__session,
                self.__auth_data,
                self.__person_data,
                self.__get_ticket_url,
            ),
            API_hotreload_file,
        )

    @error_log()
    def get_msg_id(self):
        """
        获取消息身份id
        """
        jsondata = self.get_base_request()
        jsondata.update(
            {
                "Code": 3,
                "FromUserName": self.__person_data["User"]["UserName"],
                "ToUserName": self.__person_data["User"]["UserName"],
                "ClientMsgId": Device.create_client_msg_id(),
            }
        )
        resp = self.post(
            API_webwxstatusnotify,
            params={"lang": "zh_CN", "pass_ticket": self.__auth_data["pass_ticket"]},
            json=jsondata,
        )

        self.__msg_id = resp.json()["MsgID"]

    def get_msg_signal(self):
        """
        消息信号检查
        """
        call_back = {"retcode": "0", "selector": "0"}
        try:
            resp = self.get(
                API_synccheck,
                params={
                    "r": Device.get_timestamp(),
                    "skey": self.__auth_data["skey"],
                    "sid": self.__auth_data["wxsid"],
                    "uin": self.__auth_data["wxuin"],
                    "deviceid": self.__device_id,
                    "synckey": self.create_synckey(),
                    "_": Device.get_timestamp(),
                },
                timeout=API_checktimeout,
            )
            if not resp.status_code == 200:
                raise AssertionError()
            call_back = execjs.eval(resp.text.replace("window.synccheck=", ""))
        except requests.exceptions.ReadTimeout:
            pass
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            error(e)
        time.sleep(1)
        return call_back

    @retry()
    @error_log(raise_exit=True)
    def get_msg_contents(self):
        """
        获取消息详情
        """
        jsondata = self.get_base_request()
        jsondata.update(
            {"rr": execjs.eval("~new Date"), "SyncKey": self.__person_data["SyncKey"]}
        )
        resp = self.post(
            API_webwxsync,
            params={
                "lang": "zh_CN",
                "sid": self.__auth_data["wxsid"],
                "skey": self.__auth_data["skey"],
                "pass_ticket": self.__auth_data["pass_ticket"],
            },
            json=jsondata,
        )
        resp.encoding = "utf8"
        res = resp.json()
        self.__person_data["SyncKey"] = res["SyncKey"]
        return res

    @error_log(raise_exit=True)
    def get_contact(self):
        """
        获取基础联系人
        """
        resp = self.get(
            API_webwxgetcontact,
            params={
                "lang": "zh_CN",
                "pass_ticket": self.__auth_data["pass_ticket"],
                "r": Device.get_timestamp(),
                "seq": 0,
                "skey": self.__auth_data["skey"],
            },
        )
        self.__contacts = resp.json()
        create_json(self.__contacts, API_static_path / "contacts.json")
        info(f"Get friends: [{self.__contacts['MemberCount']}]")

    @error_log()
    def get_batch_contact(self, contact_list: list = None):
        """
        获取群组联系人
        """
        if not contact_list:
            contact_list = self.__person_data["ChatSet"].split(",")

        contact_list = list(
            filter(lambda name: name in self.__person_map, contact_list)
        )

        if not contact_list:
            return

        for contact_list in [
            {"UserName": item, "EncryChatRoomId": ""}
            for item in contact_list
            if "@@" in item
        ]:
            contact_list = [contact_list]
            jsondata = self.get_base_request()
            jsondata.update({"Count": len(contact_list), "List": contact_list})
            resp = self.post(
                API_webwxbatchgetcontact,
                params={
                    "type": "ex",
                    "r": Device.get_timestamp(),
                    "lang": "zh_CN",
                    "pass_ticket": self.__auth_data["pass_ticket"],
                },
                json=jsondata,
            )
            self.__batch_contacts.update(resp.json())
        self.__person_map = Device.trans_map(self.__contacts, self.__batch_contacts)
        create_json(self.__batch_contacts, API_static_path / "batch_contacts.json")

    @error_log()
    def get_image(self, msg_id, play=False):
        """
        获得视频数据
        """
        resp = self.get(
            API_webwxgetmsgimg,
            params={"msgid": msg_id, "skey": self.__auth_data["skey"]},
        )
        if play:
            imgcat(resp.content)
        return resp.content

    @error_log()
    def get_voice(self, msg_id, play=False):
        """
        获得语音数据
        """
        resp = self.get(
            API_webwxgetvoice,
            params={"msgid": msg_id, "skey": self.__auth_data["skey"]},
        )
        if play:
            self.__voice_pool.insert(0, BytesIO(resp.content))
        return resp.content

    @error_log()
    def get_video(self, msg_id, play=False):
        """
        获得视频数据
        """
        # self.get_image(msg_id, play)
        content = BytesIO()
        for item in self.__session.get(
            API_webwxgetvideo,
            params={"msgid": msg_id, "skey": self.__auth_data["skey"]},
            headers={"Range": "bytes=0-"},
            stream=True,
        ).iter_content():
            content.write(item)
        if play:
            pass
        return content.getvalue()

    def check_online_status(self):
        """
        检查在线状态
        """
        try:
            while True:
                if not self.__is_online:
                    warning("ready for logout")
                    for name, threadTarget in self.__thread_pool.items():
                        debug(f"{name} closed!")
                        threadTarget.join()
                    success("end!")
                    sys.exit()
                time.sleep(1)
        except Exception:
            self.__is_online = False

    @error_log()
    def send_text(self, target, msg):
        """
        文本消息发送
        """
        jsondata = self.get_base_request()
        LocalID = str(execjs.eval("+new Date()"))
        jsondata.update(
            {
                "Msg": {
                    "Type": 1,
                    "Content": msg,
                    "FromUserName": self.__person_data["User"]["UserName"],
                    "ToUserName": target,
                    "LocalID": LocalID,
                    "ClientMsgId": LocalID,
                },
                "Scene": 0,
            }
        )
        fakeHeader = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json;charset=UTF-8",
            "Host": "wx.qq.com",
            "Origin": "https://wx.qq.com",
            "Referer": "https://wx.qq.com/?&lang=zh_CN",
            "User-Agent": "Webot/1.0",
        }
        resp = self.post(
            API_webwxsendmsg,
            params={"lang": "zh_CN", "pass_ticket": self.__auth_data["pass_ticket"]},
            data=json.dumps(jsondata, ensure_ascii=False).encode("utf-8"),
            headers=fakeHeader,
        )
        warning(self.translate_text(f"🤖️->【{target}】: {msg}"))
        debug(resp.json())

    @error_log()
    def send_file(self, target, filename):
        """
        文本文件发送
        """
        with pathlib.Path(filename).open("rb") as file:
            datas = file.read()
            lens = len(datas)
            self.post(
                API_webwxuploadmedia,
                params={"f": "json"},
                json={
                    "id": "WU_FILE_0",
                    "name": filename,
                    "type": filetype(BytesIO(data)).mime,
                    "lastModifiedDate": "Tue May 21 2019 00:00:00 GMT 0800 (中国标准时间)",
                    "size": lens,
                    "mediatype": "pic",
                    "uploadmediarequest": {
                        "UploadType": 2,
                        "BaseRequest": self.get_base_request(),
                        "ClientMediaId": Device.get_timestamp(),
                        "TotalLen": lens,
                        "StartPos": 0,
                        "DataLen": lens,
                        "MediaType": 4,
                        "FromUserName": self.__person_data["User"]["UserName"],
                        "ToUserName": target,
                        "FileMd5": hashlib.new("md5", datas).hexdigest(),
                    },
                    "webwx_data_ticket": self.__session.cookies.get(
                        "webwx_data_ticket", ""
                    ),
                    "pass_ticket": self.__auth_data["pass_ticket"],
                    "filename": datas,
                },
                headers={
                    "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryrUwfuyA8mLqHyBJP",
                    "DNT": "1",
                    "Origin": "https://wx.qq.com",
                    "Referer": "https://wx.qq.com/",
                    "User-Agent": "Webot/1.0",
                },
            )

    def search_friend(self, strs):
        """
        好友搜索
        """
        for index, value in enumerate(self.__contacts["MemberList"]):
            if strs in value["NickName"]:
                print(
                    f"[{index}]{value['NickName'].ljust(4)}{value['UserName'].rjust(10)}"
                )

    def index_friend(self, hashid):
        """
        好友索引
        """
        for value in self.__contacts["MemberList"]:
            if hashid == value["UserName"]:
                return value
        return {}

    def msg_worker(self):
        """
        消息处理
        """

        debug("start msg worker")

        def worker():
            debug("start main loop")
            while True:
                try:
                    sync_check_res = self.get_msg_signal()
                    debug(f"sync_check_res: {sync_check_res}")
                    retcode, selector = (
                        sync_check_res["retcode"],
                        sync_check_res["selector"],
                    )
                    if retcode == "0" and int(selector) > 0:
                        msgs = self.get_msg_contents()
                        debug(f"Contents: {msgs}")
                        for msg in msgs["AddMsgList"]:
                            _, result = self.data_ctrl(msg)
                            self.send_back(result)
                    elif retcode == "1101":
                        self.__is_online = False
                        warning("main loop offline")
                        return
                except KeyboardInterrupt:
                    return
                except Exception as e:
                    error(e)
                finally:
                    time.sleep(0.1)

        def interaction():
            """
            简单交互式面板
            """
            debug("start isnteraction")
            while True:
                if not self.__is_online or not conf.need_interaction:
                    warning("isnteraction offline")
                    return
                try:
                    cmd = input(">>>")
                    if not cmd:
                        pass
                    else:
                        print(eval(cmd))
                except Exception as e:
                    error(e)
                finally:
                    time.sleep(0.1)

        def voice():
            debug("start voice detector")
            pygame.mixer.init()
            while True:
                if not self.__is_online:
                    warning("voice detector offline")
                    return
                while self.__voice_pool:
                    pygame.mixer.music.load(self.__voice_pool.pop())
                    pygame.mixer.music.play()
                time.sleep(2)

        def trystart(item):
            try:
                item.start()
            except Exception as e:
                error(e)

        self.__thread_pool["msg_hook"] = threading.Thread(target=worker)
        self.__thread_pool["voice_hook"] = threading.Thread(target=voice)
        self.__thread_pool["interaction"] = threading.Thread(target=interaction)
        list(map(lambda item: trystart(item[1]), self.__thread_pool.items()))
        self.check_online_status()

    def msg_is_self(self, target):
        return target["FromUserName"] == self.__person_data["User"]["UserName"]

    @error_log()
    def data_ctrl(self, msg):

        """
        打印基础消息并整理
        """
        msg_type = msg["MsgType"]
        sub_type = msg["SubMsgType"]
        is_me = self.msg_is_self(msg)
        is_group = "@@" in msg["FromUserName"]
        content_header = "👥" if is_group else "💬"
        to_user_name = "" if is_group else f'-> 【{msg["ToUserName"]}】'
        func = info if is_me else success
        content = f'{content_header}【{msg["FromUserName"]}】{to_user_name}:'
        create_json(msg, str(API_static_path / "⚡️current_msg.json"))  # 实时日志分析
        result = {
            "time": msg["CreateTime"],
            "from": msg["FromUserName"],
            "from_nick": self.translate_text(msg["FromUserName"]),
            "to": msg["ToUserName"],
            "to_nick": self.translate_text(msg["ToUserName"]),
            "type": MSG_TYPES[msg_type].lower(),
            "content": "",
            "raw_content": msg["Content"],
            "is_me": is_me,
            "is_group": is_group,
        }
        self.get_batch_contact([msg["FromUserName"], msg["ToUserName"]])
        number = f"{result['time']}_{result['from_nick']}_{msg['MsgId']}"  # 消息编号
        if msg_type == MSGTYPE_TEXT:
            if sub_type == 0:
                result["content"] = msg["Content"]
            elif sub_type == 48:
                result["content"] = msg["Content"].split(":")[0]
            self.on_text(result)
        elif msg_type == MSGTYPE_VOICE:
            voice = self.get_voice(msg["MsgId"], conf.play_voice)
            filename = str(API_meida_voice_path / f"{number}.mp3")
            save_file(voice, filename)
            result["content"] = filename
            self.on_voice(result)
        elif msg_type == MSGTYPE_VIDEO:
            video = self.get_video(msg["MsgId"], True)
            filename = str(API_meida_video_path / f"{number}.mp4")
            save_file(video, filename)
            result["content"] = filename
            self.on_video(result)
        elif msg_type == MSGTYPE_IMAGE:
            image = self.get_image(msg["MsgId"], True)
            filename = str(API_meida_image_path / f"{number}.png")
            save_file(image, filename)
            result["content"] = filename
            self.on_image(result)
        elif msg_type == MSGTYPE_EMOTICON:
            urls = URLExtract().find_urls(msg["Content"])
            if not urls:
                return
            filename = str(API_meida_emoji_path / f"{number}.png")
            imgcat(get_pic(self.__session, urls[0], filename))
            result["content"] = urls[0]
            self.on_emoji(result)
        elif msg_type == MSGTYPE_APP:
            pass
            # content += "公众号推送"
        elif msg_type == MSGTYPE_STATUSNOTIFY:
            # content += "进入/退出"
            pass
        if msg_type not in [] and result["content"]:
            func(self.translate_text(content + result["content"]))

        return msg, result

    def on_text(self, msg):
        pass

    def on_video(self, msg):
        pass

    def on_voice(self, msg):
        pass

    def on_image(self, msg):
        pass

    def on_emoji(self, msg):
        pass

    def revice(self, msg):
        pass

    def send_back(self, msg):
        pass
        # """
        #     自动回复
        # """

        # if not target:
        #     target = msg["FromUserName"]
        # else:
        #     try:
        #         target = list(
        #             filter(lambda item: item[1] == target, self.__person_map.items())
        #         )[0][0]
        #     except Exception as e:
        #         print(e)

        # if target in [
        #     self.__person_data["User"]["UserName"],
        #     self.__person_data["User"]["NickName"],
        # ]:  # 判断是否为自己
        #     return

        # if "@@" in target and not groups:  # 判断是否为群组
        #     return

        # if "gh_" == self.index_friend(target).get("KeyWord", ""):  # 判断是否为公众号
        #     return

        # content = msg["Content"].replace(YOUR_NAME, "你")  # 反骂功能
        # msg_type = msg["MsgType"]
        # if msg_type == MSGTYPE_TEXT:
        #     self.send_msg(target, content)

    # def filter_msg(self)

    def translate_text(self, words):
        """
        美化消息
        """
        for k, v in self.__person_map.items():
            words = words.replace(k, v)
        return words

    @error_log()
    def run_add_on(self):

        debug("check add on")
        if conf.export_xlsx:
            Device.export_all_contact(
                self.__contacts, self.__session, self.__person_data
            )
        if conf.make_icon_wall:
            Device.make_icon_wall(
                API_media_icon_path,
                API_analysis_path / f"{self.__nick}_icon_wall.png",
                patterns="*_0",
            )
        if conf.sunburst_city:
            Device.export_sunburst_city(
                self.__contacts, API_analysis_path / f"{self.__nick}_sunburst_city.html"
            )

    @error_log(raise_exit=True)
    def run(
        self,
        hot_reload=None,
        export_xlsx=None,
        sunburst_city=None,
        make_icon_wall=None,
        debug=None,
        interaction=None,
    ):
        if hot_reload != None:
            self.__hot_reload = bool(hot_reload)
        if export_xlsx != None:
            conf.export_xlsx = bool(export_xlsx)
        if sunburst_city != None:
            conf.sunburst_city = bool(sunburst_city)
        if make_icon_wall != None:
            conf.make_icon_wall = bool(make_icon_wall)
        if debug != None:
            conf.debug = bool(debug)
        if interaction != None:
            conf.need_interaction = bool(interaction)
        self.login()
        while not self.get_ticket():
            self.__hot_reload = False
            self.login()
        self.login_success_init()
        self.get_msg_id()
        self.get_contact()
        self.get_batch_contact()
        self.run_add_on()
        self.msg_worker()


if __name__ == "__main__":
    Webot().run()
