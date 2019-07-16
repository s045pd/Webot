import copy
import os
import time
from contextlib import contextmanager

import moment
from retry import retry

from webot.conf import config
from webot.data import API_target
from webot.log import error, info, debug, debug_error_log
from urllib.parse import urljoin


@retry(delay=1)
def get_pic(session, url, full=False):
    try:
        return session.get(url if full else urljoin(API_target, url)).content
    except Exception as e:
        raise


def error_log(target="", default=None, raise_err=False, raise_exit=False):
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
def checkTimes(msg="", level=3):
    timeStart = time.time()
    yield
    info(f"{msg} cost times: {round(time.time()-timeStart,level)}s")


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


def checkPath(path):
    return os.path.exists(os.path.dirname(path))


def initPath(path):
    if not checkPath(path):
        os.makedirs(os.path.dirname(path))


def make_chunk(datas, length=512):
    data = True
    while data:
        chunk = []
        while len(chunk) < length:
            try:
                data = next(datas)
                chunk.append(data)
            except Exception as e:
                data = None
                break
        yield chunk
