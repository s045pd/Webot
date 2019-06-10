# Webot ![](https://img.shields.io/badge/language-python3-orange.svg) ![](https://img.shields.io/badge/power_by-Wechat-Green.svg)

这是一个基于web微信协议的简易微信机器人，目前功能比较简陋且不堪🙈。

### 现有功能

- 简单文字消息回复
- 实时信息展示
- 语音消息自动播报及保存
- 通讯录导出

### 环境安装

```
python3 -m pip install -r requirements.txt
```

### 案例用法
下面是一个简单的文本回复案例即```test.py```

```python
from webot.core import Webot
from webot.log import warning
from webot.data import *
from pprint import pprint

class bot(Webot):
    def send_back(self, msg):
        # pprint(msg)
        types = msg["MsgType"]
        if self.msg_is_self(msg):
            return
        if types == MSGTYPE_TEXT:
            text = msg["Content"]
            if "你好" == text:
                self.send_text(msg["FromUserName"], "你好呀！")

bot().run(True)
```
以下是运行开始的截图!

![](./media/demo.png)

### TODO

- 文件及图片发送
- 其他更多思考中的功能