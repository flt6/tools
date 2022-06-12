import cv2
import  numpy as np
import tkinter as tk
from PIL import Image,ImageTk

root=tk.Tk()
root.attributes("-transparentcolor","white")
cam=cv2.VideoCapture(2)
img12=cv2.imread('img.jpg')
print(1)
# lab=tk.Label(root,text="212",image=img2)

success,img=cam.read()
can=tk.Canvas(root,width=1920,height=1080)
def main():
    success,img=cam.read()
    img=cv2.resize(img,None,fx=1,fy=1)
    # cv2.imshow('img',img)

    #转换hsv
    grey=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    #获取mask
    mask = cv2.inRange(grey, 0, 130)
    ans=np.array(255-mask)
    # cv2.imshow('Mask', ans)
    fortk=Image.fromarray(ans)
    img2=ImageTk.PhotoImage(image=fortk)
    can.create_image((320,300),image=img2)
    can.pack()
    can.update()
    root.update()
    cv2.imshow("raw",img)
    cv2.imshow("ans",ans)
    cv2.waitKey(50)

# img2=ImageTk.PhotoImage(image=Image.fromarray(img12))

while True:
    main()
cv2.waitKey(0)
cv2.destroyAllWindows()
