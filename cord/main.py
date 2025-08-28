from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import io
import streamlit as st
# import scienceplots

# plt.style.use(['nature', 'no-latex',"cjk-sc-font"])
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def cubic_bezier_with_zero_derivatives(p0, p1, t_array, influence_factor):
    """
    创建三次贝塞尔曲线，确保起点和终点的导数为0
    
    参数:
    p0: 起点 [x0, y0]
    p1: 终点 [x1, y1]
    t_array: 参数数组 (0到1)
    influence_factor: 影响因子，控制控制点的位置
    
    返回:
    x_array, y_array: 贝塞尔曲线上的点
    """
    x0, y0 = p0
    x1, y1 = p1
    
    # 计算控制点，确保起点和终点导数为0
    # 控制点位置基于影响因子和两点间距离
    dx = x1 - x0
    
    # 第一个控制点：在起点右侧，y坐标与起点相同（确保起点导数为0）
    p1_control = [x0 + dx * influence_factor[0], y0]
    
    # 第二个控制点：在终点左侧，y坐标与终点相同（确保终点导数为0）
    p2_control = [x1 - dx * influence_factor[1], y1]
    
    # 计算贝塞尔曲线
    x_bezier = ((1-t_array)**3 * x0 + 
                3*(1-t_array)**2 * t_array * p1_control[0] + 
                3*(1-t_array) * t_array**2 * p2_control[0] + 
                t_array**3 * x1)
    
    y_bezier = ((1-t_array)**3 * y0 + 
                3*(1-t_array)**2 * t_array * p1_control[1] + 
                3*(1-t_array) * t_array**2 * p2_control[1] + 
                t_array**3 * y1)
    
    return x_bezier, y_bezier

# @st.cache_resource
def plot_reaction_coordinate(changed=None, _lines=None):
    """
    绘制反应坐标图
    """
     
    lines = []
    fig,ax1 = plt.subplots(figsize=(9, 6))

    last=(-1,-1)
    
    maxy = data["Energy"].max()
    miny = data["Energy"].min()
    varyy = maxy - miny
    
    for i in range(data.shape[0]):
        line:pd.Series = data.loc[i]
        if last == (-1,-1):
            last = (1, line["Energy"])
            if not pd.isna(line["Name"]):
                ax1.annotate(str(line["Name"]), (1, line["Energy"]+varyy*K_POS[i]), ha='center')
        else:
            p1 = last[0]+2,line["Energy"]
            x,y = cubic_bezier_with_zero_derivatives(last,p1, np.linspace(0, 1, 300), INFLU_FACTORS[(i*2-2):i*2])
            l = ax1.plot(x, y, "-", color="black")[0]
            lines.append(l)
            if not pd.isna(line["Name"]):
                p = p1[0],p1[1]+varyy*K_POS[i]
                ax1.annotate(str(line["Name"]), p, ha='center')
            last = p1
        
        

    ax1.set_xlabel("Reaction Coordinate")
    ax1.xaxis.set_ticks([])
    ax1.set_ylabel("Energy (kcal/mol)")
    ax1.set_ylim(miny-varyy*0.1, maxy+varyy*0.1)
    
    if st.session_state.get("xylim", None) is not None:
        ax1.set_xlim(st.session_state["xmin"], st.session_state["xmax"])
        ax1.set_ylim(st.session_state["ymin"], st.session_state["ymax"])
        
    return fig,lines

# 创建图形和坐标轴

def callback_gen(x,typ=0):
    if typ:
        def callback():
            global K_POS
            K_POS[x] = st.session_state.get(f'text_slider_{x}', 0.05)
            plot_reaction_coordinate(changed=x, _lines=lines)
    else:
        def callback():
            global INFLU_FACTORS
            INFLU_FACTORS[x-1] = st.session_state.get(f'slider_{x}', 0.5)
            plot_reaction_coordinate(changed=x, _lines=lines)

    return callback


def on_save():
    global out_file
    # for slider in slides:
    # slider.ax.set_visible(False)
    plt.draw()
    plt.tight_layout()
    out_file = io.BytesIO()
    fig.savefig(out_file, format=st.session_state.get("export_format", ".tiff")[1:], dpi=300, bbox_inches='tight')
    out_file.seek(0)
    return out_file.getvalue()

@st.cache_resource
def load_data(file):
    # 读取数据文件
    try:
        if st.session_state.get("use_example", False):
            data = create_example()[0]
        else:
            data = pd.read_excel(file) if file.name.endswith((".xlsx", ".xls")) else pd.read_csv(file)
        if data.columns.tolist() != ["Name", "Energy"]:
            st.warning("Format should be Name, Energy. Modified automatically.")
            data.columns = ["Name", "Energy"]
    except Exception as e:
        st.error(f"Error reading file: {e}")
        exit()

    INFLU_FACTORS = [0.5] * data.shape[0] * 2  # 动态创建数组
    
    ene = data["Energy"].to_numpy()
    K_POS = np.where(ene[1:]>ene[:1],0.03,-0.05)
    K_POS = [-0.05] + K_POS.tolist()

    data["Energy"] -= data["Energy"][0]
    data["Energy"]*=627.509

    return data, INFLU_FACTORS,K_POS

@st.cache_data
def create_example():
    tmp_file = io.BytesIO()
    example = pd.DataFrame({"Name":["reactant","TS","result"], "Energy":[-400.310327,-400.210017,-400.341576,]})
    example.to_excel(tmp_file, index=False)
    return example,tmp_file


out_file = io.BytesIO()

st.set_page_config(
    page_title="反应坐标绘制",
    page_icon=":chart_with_upwards_trend:",
    initial_sidebar_state="expanded",layout="wide"
)
st.title("反应坐标绘制")
st.write("---")

file = st.file_uploader("上传能量文件", type=["xlsx", "xls", "csv"],key="file")

if not file and not st.session_state.get("use_example", False) and "datas" not in st.session_state:
    # st.set_page_config(layout="centered")
    st.write("按照下列格式上传表格。请保证列名和范例一致，或直接下载。")
    st.warning("注意，Energy单位为Hatree，程序将自动转换为kcal/mol的相对能量")
    example,tmp_file = create_example()
    st.dataframe(example,hide_index=True)
    st.download_button("下载模板",data=tmp_file,file_name="reaction_coordinate_example.xlsx")
    def use_tmp():
        global file
        st.session_state["use_example"] = True
        file = tmp_file
    st.button("使用样例使用",on_click=use_tmp)
    st.stop()
else:
    pass
    # st.set_page_config(layout="wide")
col1,col2 = st.columns([0.4,0.6],gap="medium")


with col2:
    
    if "datas" not in st.session_state:
        data, INFLU_FACTORS,K_POS = load_data(file)
        st.session_state["datas"] = (data, INFLU_FACTORS,K_POS)
    else:
        data, INFLU_FACTORS, K_POS = st.session_state["datas"]

    fig,lines = plot_reaction_coordinate()
    stfig = st.pyplot(fig,False)
    
with col1:
    st.title("作图参数设置")
    with st.expander("调整曲线形状（贝塞尔参数）"):
        for i in range(data.shape[0]):
            if i!=0:
                st.slider(
                    f'{data.loc[i,"Name"]} 左',
                    0.0, 1.0, value=INFLU_FACTORS[i*2-1],
                    key=f'slider_{i*2}',
                    on_change=callback_gen(i*2)
                )
            if i!= data.shape[0] - 1:
                st.slider(
                    f'{data.loc[i,"Name"]} 右',
                    0.0, 1.0, value=INFLU_FACTORS[i*2],
                    key=f'slider_{i*2+1}',
                    on_change=callback_gen(i*2+1)
                )
    with st.expander("调整文字位置"):
        for i in range(data.shape[0]):
            st.slider(
                f'{data.loc[i,"Name"]}',
                -0.1, 0.1, value=K_POS[i],
                key=f'text_slider_{i}',
                on_change=callback_gen(i,1)
            )
    
    with st.expander("调整坐标系极限"):
        if st.session_state.get("xylim", None) is None:
            xmin,xmax = plt.xlim()
            ymin,ymax = plt.ylim()
            st.session_state["xylim"] = (xmin,xmax,ymin,ymax)
            
        xmin,xmax,ymin,ymax = st.session_state["xylim"]
        dxmin,dxmax,dymin,dymax = abs(xmin)*0.5,abs(xmax)*0.5,abs(ymin)*0.5,abs(ymax)*0.5

        st.slider("x min", xmin-dxmin, xmin+dxmin,value=xmin, key="xmin")
        st.slider("x max", xmax-dxmax, xmax+dxmax,value=xmax, key="xmax")
        st.slider("y min", ymin-dymin, ymin+dymin,value=ymin, key="ymin")
        st.slider("y max", ymax-dymax, ymax+dymax,value=ymax, key="ymax")
    
    with st.expander("导出"):
        st.selectbox("导出文件拓展名",[".tiff",".pdf",".png",".pgf"],key="export_format")
        btn = st.button("生成文件")
        if btn:
            st.download_button(
                    label="下载",
                    data=on_save(),
                    file_name="reaction_coordinate"+st.session_state.get("export_format", ".tiff"),
                    # mime="image/tiff"
                )
    
    st.slider("字体大小",8,20, value=12, key="font_size",
              on_change=lambda: plt.rcParams.update({'font.size': st.session_state.get("font_size", 12)}))
    if st.button("重置",type="primary"):
        st.session_state.clear()
        st.rerun()

st.write("---")
st.dataframe(data)
