import requests
from time import strftime
from re import findall

HTML_FORMAT ='''
<html>

<head>
<titile>{title}</titile>
</head>

<body>
{body}
</body>

</html>
'''

def writefile(filename,text):
    with open(filename+'.html', 'w') as f:
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
        html=response["Html"]
        # replace "data-original" to "src" for showing in browser
        html=html.replace("data-original", "src")
        writefile(strftime("%Y%m%d-%H:%M"),html)
    else:
        print("is RAR")
        rar=ret['rarPreviewInfo']
        for file in rar:
            html=file["Html"]
            title=file["SoftName"]
            # replace "data-original" to "src" for showing in browser
            # html=html.replace("data-original", "src")
            urls=findall("(?<=data-original=\")https://preview.xkw.com/.+(?=\")",html)
            l=[]
            for url in urls:
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
    main()
