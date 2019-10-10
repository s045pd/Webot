import os
import pathlib
import random
import time
from contextlib import contextmanager

import requests
from PIL import Image
from retry import retry

from webot.conf import config
from webot.log import debug, debug_error_log, error, info


@retry(delay=1)
def get_pic(session: requests.Session, url: str, name: str = ""):
    try:
        img = session.get(url).content
        if name:
            with pathlib.Path(name).open("wb") as file:
                file.write(img)
        return img
    except Exception as e:
        raise e


def error_log(
    target: str = "", default=None, raise_err: bool = False, raise_exit: bool = False
):
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__ if "__name__" in dir(func) else ""
            debug_error_log(f"start {func_name}")
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                exit()
            except Exception as e:
                error(f"[{target} {func_name}]: {e}")
                if raise_exit:
                    exit()
                elif raise_err:
                    raise e
                return default
            finally:
                debug_error_log(f"end {func_name}", False)

        return wrapper

    return decorator


@contextmanager
def check_times(msg: str = "", level: int = 3):
    timeStart = time.time()
    yield
    debug(f"{msg} cost times: {round(time.time()-timeStart,level)}s")


def checkCount(func):
    def checker(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            config.status["success"] += 1
            return res
        except Exception:
            config.status["failed"] += 1
            raise

    return checker(func)


def addsucess():
    config.status["success"] += 1


def addfailed():
    config.status["failed"] += 1


def addtotal():
    config.status["total"] += 1


def addupdate():
    config.status["updated"] += 1


def check_path(path):
    return os.path.exists(os.path.dirname(path))


def init_path(path):
    if not check_path(path):
        parent_path = os.path.dirname(path)
        os.makedirs(parent_path)
        info(f"create path: {parent_path}")
    return pathlib.Path(path)


def make_chunk(datas, length=512):
    data = True
    while data:
        chunk = []
        while len(chunk) < length:
            try:
                data = next(datas)
                chunk.append(data)
            except Exception:
                data = None
                break
        yield chunk


def random_color():
    return "#" + "".join([random.choice("0123456789abcdef") for j in range(6)])


def format_sunburst_city(data):  # 整理好友城市数据，将其变为一个可以直接使用的字典
    datas = {}
    for item in data["MemberList"]:
        province = item["Province"]
        city = item["City"]
        if len(province) > 5:
            continue
        if province not in datas:
            datas[province] = {}
        if city not in datas[province]:
            datas[province][city] = 1
        else:
            datas[province][city] += 1

    result = []
    for province, pitem in datas.items():
        result.append(
            {
                "name": province,
                "itemStyle": {"color": random_color()},
                "children": [
                    {
                        "name": city,
                        "value": citem,
                        "itemStyle": {"color": random_color()},
                    }
                    for city, citem in pitem.items()
                ],
            }
        )
    return result


def check_if_can_open(path):
    try:
        return Image.open(path)
    except Exception:
        pass
