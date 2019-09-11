import json
import pickle

import pandas

from webot.common import checkTimes, initPath


def create_xlsx(datas, columns, filename="res.xlsx"):
    with checkTimes(f"Created {filename}"):
        xlsx = pandas.DataFrame(datas)
        xlsx.rename(columns={_: __ for _, __ in enumerate(columns)}, inplace=True)
        initPath(filename)
        writer = pandas.ExcelWriter(filename, options={"strings_to_urls": False})
        xlsx.to_excel(writer, "data")
        writer.save()


def create_json(datas, filename="res.json"):
    with checkTimes(f"Saved {filename}"):
        initPath(filename)
        with open(filename, "w") as f:
            f.write(json.dumps(datas, ensure_ascii=False, indent=4))


def save_worker(data, filename="res.pkl"):
    """
        会话保存
    """
    with checkTimes(f"Saved {filename}"):
        initPath(filename)
        with open(filename, "wb") as f:
            pickle.dump((data), f)


def load_worker(filename="res.pkl"):
    """
        会话还原
    """
    with checkTimes(f"Saved {filename}"):
        initPath(filename)
        with open(filename, "rb") as f:
            return pickle.load(f)


def save_file(data, filename):
    """
        文件保存
    """
    initPath(filename)
    with open(filename, "wb") as f:
        f.write(data)
