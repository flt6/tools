from re import search
from requests import get, post
from json import dumps
from urllib.parse import unquote
from base64 import b64decode
from subprocess import run
# from pandas import DataFrame

shareKey = [
    "HQeA-W81Sh",
    "HQeA-KW1Sh",
    "HQeA-421Sh",
    "HQeA-G21Sh"
]


class Get123pan:
    page = "https://www.123pan.com/s/{}"
    share_get = "https://www.123pan.com/a/api/share/get?limit=100&next=1&orderBy=share_id&orderDirection=desc&shareKey={share}&ParentFileId={par}&Page=1"
    down = "https://www.123pan.com/a/api/share/download/info"

    @staticmethod
    def get_page(shareKey:str):
        res = get(Get123pan.page.format(shareKey))
        res.raise_for_status()
        t = res.text
        fileId = search(r'(?<=\"FileId\"\:)\d{7}',t)
        if fileId is None:
            print("No `FileId` is found!")
            print(t)
            exit(1)
        return int(fileId.group())

    @staticmethod
    def get_share(shareKey:str,fileId:int):
        res = get(Get123pan.share_get.format(share=shareKey,par=str(fileId)))
        res.raise_for_status()
        json = res.json()
        assert json['message'] == "ok" and json["code"] == 0
        data = json["data"]["InfoList"][0]
        data = {
            "FileID": data["FileId"],
            "S3keyFlag": data["S3KeyFlag"],
            "Size": data["Size"],
            "Etag": data["Etag"]
        }
        return data

    @staticmethod
    def get_url(data):
        res = post(Get123pan.down,data=dumps(data))
        res.raise_for_status()
        json = res.json()
        assert json['code'] == 0 and json["message"] == "success"
        url = json["data"]["DownloadURL"]
        url = search(r"(?<=params=).+",url)
        assert url is not None
        url = url.group()
        url = b64decode(url).decode()
        url = unquote(url)
        return url
    
    @staticmethod
    def get(shareKey:str):
        fileId = Get123pan.get_page(shareKey)
        data = Get123pan.get_share(shareKey,fileId)
        down_body = {
            "ShareKey": shareKey,
        }
        down_body.update(data)
        # print(DataFrame(data=down_body))
        return Get123pan.get_url(down_body)

if __name__ == '__main__':
    for key in shareKey:
        url = Get123pan.get(key)
        print("url: {}".format(url))
        cmd = [
            'aria2c.exe',
            '-x8',
            '-s8',
            url
        ]
        r=run(cmd)
        print("aria2c finished with {}".format(r.returncode))