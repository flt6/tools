import requests
from time import strftime
from re import findall, sub
from hashlib import md5

HTML_FORMAT ='''
<html>

<head>
<title>{title}</title>
</head>

<body>
{body}
</body>

</html>
'''

def writefile(filename,text):
    filename = sub(r"""[\*\/\\\|\<\>\? \:\.\'\"\!]""", "", filename)
    unique = md5(text.encode())
    filename += "_"+unique.hexdigest()[:5]
    filename+=".html"
    print("Writing "+filename)
    # print("-=-=-=-=\n",text,"\n-=-=-=-=")
    with open(filename+'.html', 'w', encoding="utf-8") as f:
        f.write(text)


def main():
    softID=input("ID: ")
    url = "https://www.zxxk.com/soft/Preview/FirstLoadPreviewJson?softID={}&type=3&product=1&v=2&FullPreview=true"
    response = requests.get(url.format(softID))
    if response.status_code!=200:
        print("ERROR")
        print(response.status_code)
        return -1
    ret=response.json()["data"]
    if not ret["IsSuccess"]:
        print("ERROR: IsSuccess option is not true")
        print(ret)
    if not ret['IsRar']:
        print("Not rar")
        print("TotalPage=%d" % ret['TotalPage'])
        print("SoftExt=%s" % ret['SoftExt'])
        try:
            html=ret["Html"]
            print(ret)
        except:
            print(ret)
            exit(1)
        # replace "data-original" to "src" for showing in browser
        html=html.replace("data-original", "src")
        writefile(f"{softID}",html)
    else:
        print("is RAR")
        rar=ret['rarPreviewInfo']
        for file in rar:
            html=file["Html"]
            title=file["SoftName"]
            # replace "data-original" to "src" for showing in browser
            # html=html.replace("data-original", "src")
            urls=findall("(?<=data-original=\")https://preview.xkw.com/\\S+(?=\")",html)
            l=[]
            for url in urls:
                if "jpg" in url:
                    l.append(f"<img src={url} />")
                    continue
                page=requests.get(url,cookies=response.cookies)
                if not page.status_code==200:
                    print(page)
                    print(page.status_code)
                    print(page.text)
                assert page.status_code==200
                l.append(page.text)
            format_html=HTML_FORMAT.format(title=title,body="\n".join(l))
            writefile(title,format_html)

if __name__  == "__main__":
    while True:
        main()
