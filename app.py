import streamlit as st
import json
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="GIS Color Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 辅助函数 ---
@st.cache_data
def load_data():
    """读取本地 JSON 数据库"""
    try:
        # 尝试读取两个文件（基础库+新加的）并合并，或者只读取一个
        files = ['palettes.json'] 
        all_data = []
        for file in files:
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.extend(data)
        # 去重（按名称）
        seen = set()
        unique_data = []
        for d in all_data:
            if d['name'] not in seen:
                unique_data.append(d)
                seen.add(d['name'])
        return unique_data
    except Exception:
        # 如果没有文件，返回空，避免报错
        return []

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def generate_css_gradient(colors):
    return f"linear-gradient(to right, {', '.join(colors)})"

import os

# --- 初始化数据 ---
if 'selected_ramps' not in st.session_state:
    st.session_state.selected_ramps = []

all_ramps = load_data()

# --- 侧边栏：筛选 ---
st.sidebar.title("🎬 GIS Color Studio")
st.sidebar.caption("电影级 · 空间色彩美学")

categories = ["全部"] + sorted(list(set(r.get('category', 'Uncategorized') for r in all_ramps)))
selected_cat = st.sidebar.selectbox("分类筛选", categories)
search_term = st.sidebar.text_input("搜索 (电影名/色系)", "")

# 过滤逻辑
filtered_ramps = all_ramps
if selected_cat != "全部":
    filtered_ramps = [r for r in filtered_ramps if r.get('category') == selected_cat]
if search_term:
    term = search_term.lower()
    filtered_ramps = [r for r in filtered_ramps if term in r['name'].lower() or any(term in t.lower() for t in r.get('tags', []))]

st.sidebar.divider()
st.sidebar.metric("当前显示", len(filtered_ramps))
st.sidebar.metric("总收录", len(all_ramps))

# --- 主界面：导出管理器 ---
st.title("色彩资产库")

with st.expander("📦 导出管理器 (Export Manager)", expanded=True):
    c1, c2 = st.columns([3, 1])
    with c1:
        # 提取当前筛选结果的名字
        filtered_names = [r['name'] for r in filtered_ramps]
        
        # 多选框
        selected_names = st.multiselect(
            "选择要打包下载的色带 (支持多选/搜索):",
            options=filtered_names,
            default=st.session_state.selected_ramps
        )
        
        # 全选按钮逻辑
        if st.button("全选当前筛选结果"):
            selected_names = filtered_names
            # 强制刷新UI选中状态需要一点技巧，这里简单处理
            st.session_state.selected_ramps = selected_names
            st.rerun()

    with c2:
        st.write("###") # Spacer
        # 准备下载数据
        export_data = [r for r in all_ramps if r['name'] in selected_names]
        
        if export_data:
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label=f"⬇️ 下载选中包 ({len(export_data)}个)",
                data=json_str,
                file_name="selected_movie_colors.json",
                mime="application/json",
                type="primary"
            )
        else:
            st.button("请先选择色带", disabled=True)

# --- 选项卡展示 ---
tab1, tab2 = st.tabs(["👁️ 色带预览", "🛠️ 构建工具下载"])

with tab1:
    if not filtered_ramps:
        st.info("没有找到匹配的电影色带。")
    
    # 网格展示
    cols = st.columns(3)
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 3]:
            with st.container():
                # CSS 卡片样式
                st.markdown(f"""
                <div style="
                    border:1px solid #e0e0e0; 
                    border-radius:8px; 
                    padding:12px; 
                    margin-bottom:16px; 
                    background-color: white;
                    transition: transform 0.2s;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="
                        height: 40px; 
                        width: 100%; 
                        background: {generate_css_gradient(ramp['colors'])}; 
                        border-radius: 4px;
                        margin-bottom: 8px;">
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h5 style="margin:0; font-size:14px; font-weight:600;">{ramp['name']}</h5>
                        <span style="font-size:10px; background:#f0f2f6; padding:2px 6px; rounded:4px;">{ramp.get('category')}</span>
                    </div>
                    <p style="margin:4px 0 0 0; color:#888; font-size:11px;">
                        {' · '.join(ramp.get('tags', [])[:3])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # 单个操作按钮
                b1, b2 = st.columns(2)
                
                # 下载单文件
                clr_data = generate_clr(ramp['colors'])
                b1.download_button(
                    "CLR", 
                    clr_data, 
                    file_name=f"{ramp['name']}.clr", 
                    key=f"btn_clr_{idx}",
                    help="直接下载适用于 ArcGIS 的 .clr 文件"
                )
                
                # 快速添加到选中列表（模拟）
                # 由于Streamlit的立即刷新机制，这里仅做展示，主要操作在上方多选框
                st.caption(f"Colors: {len(ramp['colors'])}")

with tab2:
    st.markdown("### 🚀 如何将下载的 JSON 转为 ArcGIS .stylx？")
    st.markdown("1. 在上方 **'导出管理器'** 中下载 JSON 文件（例如 `selected_movie_colors.json`）。")
    st.markdown("2. 下载下方的 Python 构建脚本。")
    st.markdown("3. 在 ArcGIS Pro 的 Python 窗口运行该脚本。")
    
    with open("arcgis_builder.py", "r", encoding='utf-8') as f:
            script_content = f.read()
            st.download_button(
                label="🛠️ 下载 Python 构建器脚本",
                data=script_content,
                file_name="arcgis_builder.py",
                mime="text/x-python"
            )
