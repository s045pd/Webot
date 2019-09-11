import re

from webot.common import error_log
from webot.log import success, warning
from webot.data import *


class Parser:
    @staticmethod
    @error_log(raise_err=True)
    def get_qr_code_uuid(resp):
        code = re.split(r'"|";', resp.text)[1]
        success(f"GET QRCODE_UUID --> [{code}]")
        return code

    @staticmethod
    def get_encoding(resp):
        warning(f"Current Data's Encoding [{resp.encoding}]")
        return resp.encoding

    @staticmethod
    @error_log(raise_err=True)
    def get_get_ticket_url(resp):
        return re.split(r'redirect_uri="|";', resp.text)[1] + "&fun=new&version=v2"

    @staticmethod
    @error_log(raise_err=True)
    def get_auth_data(resp):
        return {
            key: resp.html.find(key)[0].text
            for key in ["skey", "wxsid", "wxuin", "pass_ticket", "isgrayscale"]
        }
