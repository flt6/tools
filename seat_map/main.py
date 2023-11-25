import numpy as np
from pandas import DataFrame

# seat = np.arange(48,dtype=np.byte).reshape((4,2,6))
seat = np.fromfile('seat.dat',dtype=np.byte).reshape((4,2,6))
print(seat.shape)

maps = np.arange(4)
maps[-1]=maps[0]
maps[:-1]+=1

seat[:,:,-1]=seat[:,:,0]
seat[:,:,0:-1]+=1
seat = seat[maps,:,:]

seat.tofile("seat.dat")

names = np.array([
    "张姝肜",
    "乔旺源",
    "焦祺",
    "丛金旺",
    "周巧冉",
    "张日昊",
    "刘卓",
    "宋智宪",
    "张文桦",
    "王子来",
    "姜樱楠",
    "于诗澳",
    "张潇艺",
    "李语恒",
    "*",
    "张晓轩",
    "宋佳怡",
    "宋雨蔓",
    "于世函",
    "王梁宇",
    "*",
    "毕一聪",
    "娄晴",
    "黄卓琳",
    "刘宇航",
    "刘雨鑫",
    "庞惠铭",
    "徐子灏",
    "阎展博",
    "崔子豪",
    "王明仁",
    "王耀增",
    "李善伊",
    "吴庆波",
    "樊乐天",
    "潘一鸣",
    "洛艺伟",
    "周含笑",
    "苏振宇",
    "沈洁",
    "李柏畅",
    "毕思淼",
    "张濠亿",
    "李怡萱",
    "高镆",
    "张妍",
    "杨颜聪",
    "李南卓阳"
])
opt = seat.reshape((8,6))
opt = opt[:,::-1]
print(DataFrame(opt))
opt = names[opt]
with open("seat.csv", "w", encoding="gb2312") as f:
    for i in range(6):
        print(",".join(opt[:,i]),file=f)