import numpy as np
import matplotlib.pyplot as plt

# 定义初始数组和目标大小
arr = np.random.rand(10) * 10  # 随机生成10个在0到10之间的数
TARGET_SIZE = 50

# 计算数组的初始大小和每步的变化量
current_size = np.sum(arr)
steps = 100  # 逐步逼近的步数
scaling_factor = (TARGET_SIZE - current_size) / steps

# 绘图初始化
fig, ax = plt.subplots()
line, = ax.plot(arr, marker='o')
ax.set_ylim(0, max(arr) + 10)

# 逐步逼近目标
for i in range(steps):
    arr += scaling_factor * (arr / np.sum(arr))  # 按比例调整数组元素
    line.set_ydata(arr)  # 更新线条数据
    plt.title(f'Step {i+1}: Size = {np.sum(arr):.2f}')
    plt.pause(0.1)  # 动态显示每一步
plt.show()
