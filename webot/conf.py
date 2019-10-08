class config:
    name = "spider"
    my_id = ""
    debug = False
    play_voice = True
    export_xlsx = False
    make_icon_wall = True
    sunburst_city = True

    need_interaction = False

    fakeHeader = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "max-age=0",
        "user-agent": "Webot/1.0",
    }

    status = {"success": 0, "failed": 0, "total": 0, "updated": 0}
    defaultstatus = {"success": 0, "failed": 0, "total": 0, "updated": 0}
    db = "work"


conf = config
