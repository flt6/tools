from requests import get
from bs4 import BeautifulSoup
from pickle import dump,load
from traceback import print_exc

SAV_COOKIE=True
DEBUG=True

try:
    with open("cookies.txt","rb") as f:
        head=load(f)
        print("Used cookies.txt.")
        print("If you want to change account, please delete cookie.txt")
except IOError:
    if DEBUG:
        print_exc()
        cook=input("Please input cookie: ")
        head={"Cookie": cook}
    else:
        print("Can't read cookie.txt!")
        print("If you use this program for thhe first time, please ignore this.")
        print("Set DEBUG at the start of file to see debug information.")
        cook=input("Please input cookie: ")
        head={"Cookie": cook}
except Exception:
    if DEBUG:
        print_exc()
        cook=input("Please input cookie: ")
        head={"Cookie": cook}
    else:
        print("Can't read cookie.txt!")
        cook=input("Please input cookie: ")
        head={"Cookie": cook}

url=input("Please input URL: ")
try:
    if SAV_COOKIE:
        with open("cookies.txt","wb") as f:
            dump(head,f)
except Exception:
    if DEBUG:
        print_exc()
    else:
        print("Can't save cookie.txt!")
base='''<!DOCTYPE html>
<html lang="zh-cn">
    <head>
        <meta charset="utf-8"/>
        <meta name="renderer" content="webkit"/>
        <style type="text/css">
            .list-box {
                width: 21cm;
            }
            div,label{
                font-size: 20px !important;
                line-height: 50px !important;
            }
        </style>
        <link href="https://img.jyeoo.net/jye-root-3.0.css?v=20211228" rel="stylesheet" type="text/css"/>
        <link href="https://img.jyeoo.net/images/formula/style_math.css?v=20211028" rel="stylesheet" type="text/css"/>
    </head>
    <body>
        <div class="content">
            <div class="wrapper clearfix">
                <ul class="ques-list list-box">

                </ul>
            </div>
        </div>
    </body>
</html>
'''
try:
    t=get(url,headers=head).text
except Exception:
    print("GET %s failed."%(url,))
    if DEBUG:
        print_exc()
    else:
        print("Please try again or check the URL and the Internet.")
    exit(-1)    
print("GET %s succeed."%(url,))

try:
    root=BeautifulSoup(t,features="lxml")
    file=BeautifulSoup(base,features="lxml")
    new=file.find_all("div",class_="wrapper clearfix")[0].ul
    a=root.find_all("li",class_="QUES_LI")
    
    if DEBUG:print("Prepare parse succeed")

    for i in a:
        for tem in i.find_all("label",class_='s'):
            if DEBUG:
                print("[*] Found answer in html:\n"+tem.prettify())
            tem["class"]=""
        for tem in i.find_all("div",class_='quizPutTag'):
            if DEBUG:
                print("[*] Found answer in html:\n"+tem.prettify())
            tem.contents=[]
        new.append(i.fieldset)
    if len(a)==0:
        print("Warning: 获取数据为空，请用浏览器访问网址检查是否是试卷界面。")
    else:
        print("Parse succeed.")
except Exception:
    if DEBUG:
        print_exc()
    else:
        print("Parse failed.")
    exit(-1)

try:
    st=file.new_string("答案")
    tag_p=file.new_tag("p")
    h1=file.new_tag("b")
    h1.contents.append(st)
    tag_p.append(h1)
    new.append(tag_p)
    sub=url.split("/")[3]
    url="http://www.jyeoo.com/{}/ques/detail/%s".format(sub)
    a=BeautifulSoup(t,features="lxml").find_all("li",class_="QUES_LI")
    if DEBUG:print("Get answer page succeed.")
except Exception:
    if DEBUG:
        print_exc()
    else:
        print("Prepare for geting answer failed.")
    exit(-1)

for i in range(len(a)):
    print("fetching the answer of T%d..."%(i+1))
    try:
        tem=get(url%(a[i].fieldset["id"],),headers=head)
    except Exception:
        print("GET %s failed."%(url%(a[i].fieldset["id"],),))
        if DEBUG:
            print_exc()
        else:
            print("Please try again or check the URL and the Internet.")
        exit(-1)
    try:
        tem=BeautifulSoup(tem.text,features="lxml")
        t2=tem.find("fieldset").find("div",{"class":"pt11"})
        if "见试题解答内容" in t2.text:
            t2=tem.find("fieldset").find("div",{"class":"pt6"})
        st=file.new_string("T%d："%(i+1,))
        tag=file.new_tag("b")
        tag.contents.append(st)
        new.append(tag)
        new.append(t2)
    except Exception:
        if DEBUG:
            print_exc()
        else:
            print("Get answer Error.")
        exit(-1)

try:
    with open("file.html","w",encoding="utf-8") as f:
        print(file.prettify(),file=f)
except Exception:
    if DEBUG:
        print_exc()
    else:
        print("Write file error.")
        print("Please check if there is a file named 'file.html;")
        print("If so, please rename it.")