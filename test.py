from webot.core import Webot
from webot.util import Device


class bot(Webot):
    @Device.filters(["text"], is_me=True)
    def send_back(self, msg):
        ...
        # if msg["type"] == "text":
        #     if "你好" == msg["content"]:
        #         self.send_text(msg["from"], "你好呀！")


bot().run(hot_reload=True)
