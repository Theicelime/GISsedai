import streamlit as st
import json
import pandas as pd
import os

# 页面配置
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 辅助函数 ---
def load_data():
    """读取本地 JSON 数据库"""
    try:
        with open('palettes.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("未找到 palettes.json 文件！请确保数据文件在同一目录。")
        return []

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def generate_clr(colors):
    """生成 ArcGIS CLR 格式内容"""
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        # .clr 格式: 索引 R G B
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def generate_css_gradient(colors):
    return f"linear-gradient(to right, {', '.join(colors)})"

# --- 侧边栏：筛选与管理 ---
st.sidebar.title("🎨 GIS Color Studio")
st.sidebar.markdown("专业制图色彩管理系统")

# 加载数据
all_ramps = load_data()

# 筛选器
st.sidebar.header("筛选")
categories = ["全部"] + sorted(list(set(r['category'] for r in all_ramps)))
selected_cat = st.sidebar.selectbox("分类", categories)

search_term = st.sidebar.text_input("搜索 (名称/标签)", "")

# 过滤逻辑
filtered_ramps = all_ramps
if selected_cat != "全部":
    filtered_ramps = [r for r in filtered_ramps if r['category'] == selected_cat]
if search_term:
    filtered_ramps = [r for r in filtered_ramps if search_term.lower() in r['name'].lower() or any(search_term.lower() in t.lower() for t in r['tags'])]

st.sidebar.info(f"显示: {len(filtered_ramps)} / {len(all_ramps)}")

# 可持续性扩展提示
with st.sidebar.expander("➕ 如何添加新色带?"):
    st.markdown("""
    1. 打开项目文件夹中的 `palettes.json`。
    2. 按照格式添加新的 JSON 对象：
    ```json
    {
      "name": "My Movie",
      "category": "Movies",
      "tags": ["New"],
      "colors": ["#000", "#FFF"]
    }
    ```
    3. 刷新网页即可。
    """)

# --- 主界面 ---
st.title("色彩资产库")

# 选项卡
tab1, tab2 = st.tabs(["浏览与下载", "批量生成 Stylx"])

with tab1:
    if not filtered_ramps:
        st.warning("没有找到匹配的色带。")
    
    # 网格布局展示
    cols = st.columns(3)
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 3]:
            # 渲染卡片
            with st.container():
                st.markdown(f"""
                <div style="
                    border:1px solid #ddd; 
                    border-radius:10px; 
                    padding:10px; 
                    margin-bottom:20px; 
                    background-color: white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="
                        height: 50px; 
                        width: 100%; 
                        background: {generate_css_gradient(ramp['colors'])}; 
                        border-radius: 6px;
                        margin-bottom: 8px;">
                    </div>
                    <h4 style="margin:0; padding:0; font-size:16px;">{ramp['name']}</h4>
                    <p style="margin:0; color:#666; font-size:12px;">{ramp['category']} | {len(ramp['colors'])} Colors</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 下载按钮区
                c1, c2 = st.columns(2)
                
                # CLR 下载
                clr_data = generate_clr(ramp['colors'])
                c1.download_button(
                    label="下载 .clr",
                    data=clr_data,
                    file_name=f"{ramp['name'].replace(' ', '_')}.clr",
                    mime="text/plain",
                    key=f"dl_clr_{idx}"
                )

                # TXT 下载 (RGB)
                txt_data = "\n".join([f"{hex_to_rgb(c)}" for c in ramp['colors']])
                c2.download_button(
                    label="下载 RGB",
                    data=txt_data,
                    file_name=f"{ramp['name'].replace(' ', '_')}_rgb.txt",
                    mime="text/plain",
                    key=f"dl_txt_{idx}"
                )

with tab2:
    st.header("ArcGIS Pro 样式包构建器")
    st.markdown("""
    由于 Web 端无法直接生成 Esri 二进制格式 (.stylx)，我们采用 **“数据包 + 本地构建”** 的专业模式。
    此方法 100% 保证生成的文件在 ArcGIS Pro 中可用，且支持无限量色带导入。
    """)
    
    st.markdown("### 第 1 步：下载数据包与脚本")
    
    c1, c2 = st.columns(2)
    
    # 1. 下载 JSON 数据包
    json_str = json.dumps(all_ramps, indent=2)
    c1.download_button(
        label="📦 下载全量数据包 (json)",
        data=json_str,
        file_name="arcgis_color_data.json",
        mime="application/json",
        use_container_width=True
    )
    
    # 2. 下载构建脚本
    try:
        with open("arcgis_builder.py", "r", encoding='utf-8') as f:
            script_content = f.read()
            c2.download_button(
                label="🛠️ 下载 Python 构建器",
                data=script_content,
                file_name="arcgis_builder.py",
                mime="text/x-python",
                use_container_width=True
            )
    except FileNotFoundError:
        st.error("未找到 builder 脚本文件")

    st.markdown("### 第 2 步：构建 .stylx 文件")
    st.code("""
    # 方法 A: 在 ArcGIS Pro 中运行
    1. 打开 ArcGIS Pro -> "分析" -> "Python" 窗口
    2. 将下载的 arcgis_builder.py 内容复制粘贴进去
    3. 确保 arcgis_color_data.json 的路径正确，回车运行

    # 方法 B: 使用系统 Python (需安装 arcpy)
    python arcgis_builder.py
    """, language="bash")
    
    st.success("运行完成后，你将获得一个名为 'My_GIS_Colors.stylx' 的文件，直接在 ArcGIS Pro 中添加即可使用所有 50+ 个色带！")
