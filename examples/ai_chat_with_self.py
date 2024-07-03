import sys
sys.path.append('..')

from webot.core import Webot
from webot.util import Device
import ollama

ollama.pull('llama3')

class bot(Webot):
    @Device.filters(["text"], is_me=True)
    def send_back(self, msg):
        response = ollama.chat(
            model="llama3",
            messages=[
                {
                    "role": "user",
                    "content": msg["content"],
                },
            ],
        )
        self.send_text(msg["from"], response["message"]["content"])
      


bot().run(hot_reload=True)
