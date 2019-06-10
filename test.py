from webot.core import Webot
from webot.log import warning
from webot.data import *
from pprint import pprint


class bot(Webot):
    def send_back(self, msg):
        types = msg["MsgType"]
        if self.msg_is_self(msg):
            return
        if types == MSGTYPE_TEXT:
            text = msg["Content"]
            if "你好" == text:
                self.send_text(msg["FromUserName"], "你好呀！")


bot().run(False, False)
