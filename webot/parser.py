import re

import requests

from webot.common import error_log
from webot.data import *
from webot.log import success, warning


class Parser:
    @staticmethod
    @error_log(raise_err=True)
    def get_qr_code_uuid(resp: requests.Response) -> str:
        code = re.split(r'"|";', resp.text)[1]
        success(f"GET QRCODE_UUID --> [{code}]")
        return code

    @staticmethod
    def get_encoding(resp: requests.Response) -> str:
        warning(f"Current Data's Encoding [{resp.encoding}]")
        return resp.encoding

    @staticmethod
    @error_log(raise_err=True)
    def get_get_ticket_url(resp: requests.Response) -> str:
        return re.split(r'redirect_uri="|";', resp.text)[1] + "&fun=new&version=v2"

    @staticmethod
    @error_log(raise_err=True)
    def get_auth_data(resp: requests.Response) -> dict:
        return {
            key: resp.html.find(key)[0].text
            for key in ["skey", "wxsid", "wxuin", "pass_ticket", "isgrayscale"]
        }
