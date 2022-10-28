import cv2
import numpy as np
from winsound import PlaySound,SND_ALIAS,SND_ASYNC
from time import time
# Beep(500,500)

# camera = cv2.VideoCapture(0) # 参数0表示第一个摄像头
# camera = cv2.VideoCapture("opt.flv")
camera = cv2.VideoCapture("http://192.168.124.17:8081/live.flv")
# 判断视频是否打开
if (camera.isOpened()):
    print('Open')
else:
    print('摄像头未打开')
    
# 测试用,查看视频size
size = (int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)), int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)))
print('size:'+repr(size))

es = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 4))
kernel = np.ones((5, 5), np.uint8)
background = None
cnt = 0
tot = 0
last = time()
mask = np.array([(0, 0),(282, 0),(282, 26),(0, 26)])

# cv2.waitKey(5)

while True:
# 读取视频流
    try:
        grabbed, frame_lwpCV = camera.read()
        cv2.waitKey(5)
        cv2.fillConvexPoly(frame_lwpCV, mask,(0,255,0))
        cv2.imshow("src",frame_lwpCV)
    except cv2.error:
        print("ignore this frame")
        continue
# 对帧进行预处理，先转灰度图，再进行高斯滤波。
# 用高斯滤波进行模糊处理，进行处理的原因：每个输入的视频都会因自然震动、光照变化或者摄像头本身等原因而产生噪声。对噪声进行平滑是为了避免在运动和跟踪时将其检测出来。
    gray_lwpCV = cv2.cvtColor(frame_lwpCV, cv2.COLOR_BGR2GRAY)
    gray_lwpCV = cv2.GaussianBlur(gray_lwpCV, (21, 21), 0)
# 将第一帧设置为整个输入的背景
    if background is None:
        background = gray_lwpCV
        continue
# 对于每个从背景之后读取的帧都会计算其与北京之间的差异，并得到一个差分图（different map）。
# 还需要应用阈值来得到一幅黑白图像，并通过下面代码来膨胀（dilate）图像，从而对孔（hole）和缺陷（imperfection）进行归一化处理
    diff = cv2.absdiff(background, gray_lwpCV)
    # cv2.imshow('abs', diff)
    diff = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1] # 二值化阈值处理
    diff = cv2.dilate(diff, es, iterations=2) # 形态学膨胀
# 显示矩形框
    contours, hierarchy = cv2.findContours(diff.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # 该函数计算一幅图像中目标的轮廓
    contours = [c for c in contours if cv2.contourArea(c) >= 1500]
    # 对于矩形区域，只显示大于给定阈值的轮廓，所以一些微小的变化不会显示。对于光照不变和噪声低的摄像头可不设定轮廓最小尺寸的阈值
    total=0
    for c in contours:
        # if cv2.contourArea(c) < 1500: 
        #     continue
        total += cv2.contourArea(c)
        (x, y, w, h) = cv2.boundingRect(c) # 该函数计算矩形的边界框
        cv2.rectangle(frame_lwpCV, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
    cv2.imshow('contours', frame_lwpCV)
    cv2.imshow('dis', diff)

    if len(contours)>0 and total>10000:
        cnt+=1
        if cnt > 5:
            if time()-last<5:
                print(time(),last)
                tot+=1
            else:
                print("else: ",time(),last)
                tot = 1
            last = time()
            cnt = 0
            print("################################")
            PlaySound("SystemAsterisk",SND_ALIAS|SND_ASYNC)
            background = gray_lwpCV
    else:
        cnt=cnt-1 if cnt>0 else 0
    
    if tot>4:
        PlaySound("SystemHand",SND_ALIAS)
        exit()

    key = cv2.waitKey(1) & 0xFF
# 按'L'健退出循环
    if key == ord('L'):
        break


camera.release()
cv2.destroyAllWindows()
