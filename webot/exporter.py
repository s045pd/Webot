import json
import pathlib
import pickle

import pandas

from webot.common import check_times, init_path


def create_xlsx(data: dict, columns: list, filename: str = "res.xlsx"):
    with check_times(f"Created {filename}"):
        xlsx = pandas.DataFrame(data)
        xlsx.rename(columns={_: __ for _, __ in enumerate(columns)}, inplace=True)
        init_path(filename)
        writer = pandas.ExcelWriter(filename, options={"strings_to_urls": False})
        xlsx.to_excel(writer, "data")
        writer.save()


def create_json(data: dict, filename: str = "res.json"):
    with check_times(f"Saved {filename}"):
        init_path(filename)
        with pathlib.Path(filename).open("w") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))


def save_worker(data: dict, filename: str = "res.pkl"):
    """
    会话保存
    """
    with check_times(f"Saved {filename}"):
        init_path(filename)
        with pathlib.Path(filename).open("wb") as f:
            pickle.dump((data), f)


def load_worker(filename: str = "res.pkl") -> object:
    """
    会话还原
    """
    with check_times(f"Saved {filename}"):
        with pathlib.Path(filename).open("rb") as f:
            return pickle.load(f)


def save_file(data: str, filename: str) -> None:
    """
    文件保存
    """
    init_path(filename)
    with pathlib.Path(filename).open("wb") as f:
        f.write(data)
