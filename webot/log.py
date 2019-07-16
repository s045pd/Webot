import logging

from termcolor import colored

from webot.conf import config


def makeStatus(status=True):
    return (
        f"🏠:{colored(config.status['total'],'blue')} 🌀:{colored(config.status['updated'],'blue')} ✅:{colored(config.status['success'],'green')} 🚫:{colored(config.status['failed'],'red')}] "
        if status
        else ""
    )


logging.basicConfig(format="[%(asctime)s]%(message)s", level=logging.INFO)
Loger = logging.getLogger(config.name)


def info(data, status=False):
    Loger.info(f"{makeStatus(status)}{colored(data, 'blue')}")
    return data


def success(data, status=False):
    Loger.info(f"{makeStatus(status)}{colored(data, 'green')}")
    return data


def warning(data, status=False):
    Loger.warning(f"{makeStatus(status)}{colored(data, 'yellow')}")
    return data


def error(data, status=False):
    Loger.error(f"{makeStatus(status)}{colored(data, 'red')}")
    return data


def debug(data):
    if config.debug:
        Loger.info(f"{colored(data,'cyan')}")
    return data


def debug_error_log(data, is_start=True):
    if config.debug:
        Loger.info(f"{colored(data,'cyan' if is_start else 'red' )}")
    return data


def error_exit(data, status=False):
    Loger.error(colored(data, "red"))
    exit()
