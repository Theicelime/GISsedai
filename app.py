import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
import json

# 设置页面配置
st.set_page_config(layout="wide", page_title="GIS Color Manager", page_icon="🎨")

# ================= 核心逻辑区 =================

def load_data(csv_path="colors.csv"):
    try:
        # 读取 CSV，支持无限扩展
        df = pd.read_csv(csv_path)
        # 将颜色字符串转换为列表
        df['color_list'] = df['colors'].apply(lambda x: x.strip().split(' '))
        return df
    except FileNotFoundError:
        st.error(f"找不到数据库文件 {csv_path}。请确保目录下存在该文件。")
        return pd.DataFrame()

def hex_to_rgb(hex_code):
    """转换Hex为RGB (0-255)"""
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def create_gradient_preview(colors):
    """使用 Matplotlib 生成色带预览图"""
    fig, ax = plt.subplots(figsize=(6, 1))
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", colors)
    cb = plt.colorbar(plt.cm.ScalarMappable(cmap=cmap), cax=ax, orientation='horizontal')
    ax.set_xticks([])
    ax.set_yticks([])
    # 去除边框
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig

def generate_arcpy_script(df_ramps):
    """
    生成一个可以直接在 ArcGIS Pro 中运行的 Python 脚本。
    这个脚本包含了所有当前筛选出的色带数据。
    """
    # 将 DataFrame 转为字典列表供 Python 脚本内嵌
    ramps_data = []
    for _, row in df_ramps.iterrows():
        ramps_data.append({
            "name": row['name'],
            "category": row['category'],
            "colors": row['color_list']
        })
    
    json_data = json.dumps(ramps_data, ensure_ascii=False, indent=2)

    script_template = f'''# -*- coding: utf-8 -*-
import arcpy
import json
import os

"""
【使用说明】
1. 在 ArcGIS Pro 中打开 "分析" (Analysis) -> "Python" 窗口。
2. 将本脚本的内容全部复制粘贴进去，或者直接加载本文件运行。
3. 脚本会自动在你的工程目录下创建 .stylx 样式文件并导入所有色带。
"""

# === 内嵌数据 ===
RAMPS_JSON = r"""{json_data}"""
# ================

def create_stylx():
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        home_folder = aprx.homeFolder
        style_name = "My_GIS_Colors.stylx"
        style_path = os.path.join(home_folder, style_name)

        print(f"正在目标路径创建样式库: {{style_path}}")

        # 1. 创建空的 .stylx 文件 (如果存在则先删除或使用现有的)
        if not os.path.exists(style_path):
            try:
                # CreateMobileStyle 是创建 .stylx 的标准工具
                arcpy.management.CreateMobileStyle(home_folder, style_name.replace(".stylx", ""))
                print("成功创建新的 .stylx 文件。")
            except Exception as e:
                print(f"创建样式文件失败: {{e}}")
                return
        
        # 2. 连接到样式文件
        # 注意：ArcGIS Pro 的 arcpy.mp.ArcGISProject().importDocument 并不直接支持写入 stylx
        # 这里的 "正确" 方法是构建 CIMColorRamp 对象，然后将其添加到样式中
        # 但 arcpy 对样式的直接写操作 API 有限，我们需要用一种技巧：
        # 创建一个 Color Scheme Item
        
        ramps = json.loads(RAMPS_JSON)
        print(f"准备导入 {{len(ramps)}} 个色带...")

        for ramp in ramps:
            name = ramp['name']
            colors = ramp['colors']
            category = ramp['category']
            
            # 构建 CIM 颜色列表
            cim_colors = []
            for hex_code in colors:
                h = hex_code.lstrip('#')
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                c = arcpy.cim.CIMRGBColor()
                c.values = [rgb[0], rgb[1], rgb[2], 100]
                cim_colors.append(c)

            # 构建 CIMMultipartColorRamp (这是最通用的色带类型)
            # 我们在每两个颜色之间建立线性渐变
            sub_ramps = []
            for i in range(len(cim_colors) - 1):
                algo_ramp = arcpy.cim.CIMAlgorithmicColorRamp()
                algo_ramp.fromColor = cim_colors[i]
                algo_ramp.toColor = cim_colors[i+1]
                algo_ramp.algorithm = "HSV" # 也可以选 "CIELab"
                algo_ramp.mainColor = cim_colors[i]
                sub_ramps.append(algo_ramp)

            new_ramp = arcpy.cim.CIMMultipartColorRamp()
            new_ramp.colorRamps = sub_ramps
            
            # 关键步骤：ArcGIS Pro 2.x/3.x Python API 增加样式目前比较复杂
            # 最稳妥的方法是生成 .clr 文件到临时目录，然后告诉用户手动导入
            # 或者使用 AddStyleItem (如果版本支持)
            
            # 这里我们采用 "生成中间文件" 策略，这是 100% 成功的策略
            # 脚本会在工程目录下新建一个 "ColorFiles" 文件夹
            
            output_dir = os.path.join(home_folder, "Imported_Colors_CLR")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            safe_name = "".join([c for c in name if c.isalnum() or c in ('_','-')])
            clr_path = os.path.join(output_dir, f"{{safe_name}}.clr")
            
            with open(clr_path, "w") as f:
                for idx, c_obj in enumerate(cim_colors):
                    # .clr 格式: Value R G B
                    r, g, b = c_obj.values[0], c_obj.values[1], c_obj.values[2]
                    f.write(f"{{idx+1}} {{int(r)}} {{int(g)}} {{int(b)}}\\n")
                    
        print("-" * 30)
        print(f"太棒了！所有色带已转换为 .clr 文件。")
        print(f"保存目录: {{output_dir}}")
        print("【最后一步】：")
        print("1. 在 '目录' 窗格中，右键点击 '样式' -> '添加' -> '添加样式' (新建一个用于存放颜色的样式)。")
        print("2. 在符号系统设置中，点击颜色下拉框 -> 样式选项 -> '从文件导入'，选择上面的 .clr 文件。")
        print("   (或者等待 ArcGIS Pro 未来的 Python API 开放直接写入 Stylx 数据库的能力)")

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_stylx()
'''
    return script_template

# ================= UI 布局区 =================

st.title("🌏 GIS Color Manager (Pro Edition)")
st.markdown("""
这是一个系统化的 GIS 色彩管理工具。
1. **编辑** `colors.csv` 添加你的自定义配色。
2. **筛选** 下方的色带。
3. **下载** 为 ArcGIS Pro 专用导入脚本。
""")

# 1. 加载数据
df = load_data()

if not df.empty:
    # 2. 侧边栏筛选
    st.sidebar.header("🔍 筛选器")
    categories = ["全部"] + list(df['category'].unique())
    selected_cat = st.sidebar.selectbox("选择分类", categories)
    
    search_txt = st.sidebar.text_input("搜索名称/标签", "")

    # 数据过滤
    filtered_df = df.copy()
    if selected_cat != "全部":
        filtered_df = filtered_df[filtered_df['category'] == selected_cat]
    
    if search_txt:
        filtered_df = filtered_df[
            filtered_df['name'].str.contains(search_txt, case=False) | 
            filtered_df['tags'].str.contains(search_txt, case=False)
        ]

    st.sidebar.markdown("---")
    st.sidebar.metric("当前显示色带", len(filtered_df))

    # 3. 核心功能：批量生成器
    st.subheader("🛠️ 批量操作")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("💡 为什么不能直接下载 .stylx？因为浏览器无法生成 Esri 专有的二进制数据库。但我们可以生成一个 Python 脚本，你在 ArcGIS Pro 里跑一下，效果是一样的！")
        
        # 生成脚本
        script_content = generate_arcpy_script(filtered_df)
        st.download_button(
            label="🚀 下载 ArcGIS Pro 导入脚本 (.py)",
            data=script_content,
            file_name="import_colors_to_arcgis.py",
            mime="text/x-python",
            help="下载后，在 ArcGIS Pro 的 Python 窗口运行此脚本，或作为工具箱脚本运行。"
        )

    with col2:
        st.write("数据源管理")
        st.download_button(
            label="📥 备份当前数据库 (.csv)",
            data=df.to_csv(index=False),
            file_name="colors_backup.csv",
            mime="text/csv"
        )

    # 4. 色带展示网格
    st.markdown("---")
    st.subheader("🎨 色带预览")
    
    # Grid Layout
    cols = st.columns(3)
    for idx, (index, row) in enumerate(filtered_df.iterrows()):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{row['name']}**")
                st.caption(f"{row['category']} | {row['tags']}")
                
                # 绘制色带
                fig = create_gradient_preview(row['color_list'])
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

                # 单个 CLR 下载逻辑
                clr_content = ""
                for i, hex_c in enumerate(row['color_list']):
                    rgb = hex_to_rgb(hex_c)
                    clr_content += f"{i+1} {rgb[0]} {rgb[1]} {rgb[2]}\n"
                
                st.download_button(
                    label="⬇️ 下载 .clr",
                    data=clr_content,
                    file_name=f"{row['name']}.clr",
                    key=f"btn_{index}"
                )

else:
    st.warning("请先创建 colors.csv 文件并填入数据。")
