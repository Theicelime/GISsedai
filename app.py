import streamlit as st
import json
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ==========================================
# 1. 核心配置 & Apple 风格 CSS (保持原有精髓)
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全局字体 */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #F5F5F7;
        color: #1D1D1F;
    }
    
    /* 侧边栏优化 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0,0,0,0.06);
    }

    /* 卡片容器 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 10px;
        margin-bottom: 15px;
        border: 1px solid rgba(0,0,0,0.04);
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
        position: relative;
    }
    .apple-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.08);
    }

    /* 色带条 */
    .gradient-bar {
        height: 50px;
        width: 100%;
        border-radius: 12px;
        margin-bottom: 8px;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); 
    }

    /* 标题 */
    .card-title {
        font-size: 13px;
        font-weight: 600;
        color: #333;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 8px;
    }

    /* 按钮组样式优化 */
    div.stButton > button {
        border-radius: 14px !important;
        border: none !important;
        background-color: #F2F2F7 !important;
        color: #007AFF !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        padding: 0px 0px !important;
        height: 28px !important;
        width: 100% !important;
        transition: all 0.1s;
    }
    div.stButton > button:hover {
        background-color: #007AFF !important;
        color: white !important;
    }
    
    /* 删除按钮红色特化 */
    div[data-testid="column"] button[kind="primary"] {
        background-color: #FF3B30 !important; /* Apple Red */
        color: white !important;
        opacity: 0.8;
    }
    div[data-testid="column"] button[kind="primary"]:hover {
        opacity: 1.0;
    }

    /* 可视化画框容器 */
    .viz-stage {
        background-color: #FFFFFF;
        border-radius: 24px;
        padding: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        text-align: center;
        margin: 0 auto 40px auto;
        max-width: 900px;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    .viz-header {
        font-size: 14px;
        color: #86868B;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 隐藏 Streamlit 头部 */
    header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑处理
# ==========================================
def init_session():
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []
    if 'preview_colors' not in st.session_state:
        st.session_state.preview_colors = None
    if 'preview_name' not in st.session_state:
        st.session_state.preview_name = None

def toggle_ramp_select(name):
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

def set_preview(name, colors):
    st.session_state.preview_name = name
    st.session_state.preview_colors = colors

# --- 新增：永久删除功能 ---
def delete_ramp_permanent(name_to_delete):
    # 1. 读取当前文件
    current_data, _ = load_data_raw()
    
    # 2. 过滤掉要删除的项
    new_data = [r for r in current_data if r['name'] != name_to_delete]
    
    # 3. 写入回文件
    try:
        with open('palettes.json', 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        
        # 4. 清理 session state 防止引用不存在的数据
        if name_to_delete in st.session_state.selected_ramps:
            st.session_state.selected_ramps.remove(name_to_delete)
        if st.session_state.preview_name == name_to_delete:
            st.session_state.preview_name = None
            st.session_state.preview_colors = None
            
        st.rerun() # 立即刷新页面
    except Exception as e:
        st.error(f"删除失败: {e}")

def hex_to_rgb(hex_code):
    try:
        h = hex_code.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (0,0,0)

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def get_gradient_css(colors):
    return f"linear-gradient(to right, {', '.join(colors)})"

# --- 优化后的绘图函数 ---
def plot_dem_optimized(dem_file, colors):
    """
    针对 40MB 级别 DEM 的高清优化渲染
    """
    with rasterio.open(dem_file) as src:
        # 1. 读取数据
        # 你的数据只有40MB，我们可以稍微放宽降采样限制，让图更清楚
        # 设置最大边长为 1600 像素 (比之前的 800 更清晰)
        max_dim = 1600 
        scale = min(1.0, max_dim / max(src.width, src.height))
        
        if scale < 1.0:
            new_height = int(src.height * scale)
            new_width = int(src.width * scale)
            # 使用 bilinear 插值，比 nearest 更平滑
            data = src.read(1, out_shape=(new_height, new_width), resampling=rasterio.enums.Resampling.bilinear)
        else:
            data = src.read(1)
            
        # 2. 处理 NoData 和 0 值 (关键修改)
        data = data.astype('float32')
        
        # 如果原始文件有 nodata 定义，先处理
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        
        # 【核心】强制将 0 值设为 NaN (透明)，去除黑边
        data[data == 0] = np.nan

    # 3. 绘图配置 (更小尺寸，更高 DPI = 更精细)
    cmap = LinearSegmentedColormap.from_list("custom_ramp", colors)
    
    # figsize=(8, 5) 配合 dpi=150，在网页上显示大小适中但非常清晰
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    
    # 移除所有边框和坐标轴
    ax.axis('off')
    
    # 设置背景透明
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    
    # 绘制
    ax.imshow(data, cmap=cmap, interpolation='bilinear')
    
    # 去除留白
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0,0)
    
    return fig

# 不使用缓存读取，确保删除操作能实时反映
def load_data_raw():
    file_path = 'palettes.json'
    if not os.path.exists(file_path):
        return [], None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 展平逻辑
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                flat = []
                for sub in data: flat.extend(sub)
                data = flat
            return data, None
    except Exception as e:
        return [], str(e)

# ==========================================
# 3. 页面渲染流程
# ==========================================
init_session()
all_ramps, err = load_data_raw()

if err:
    st.error(f"JSON 数据错误: {err}")
    st.stop()

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("###  Color Studio")
    
    # DEM 上传
    st.markdown("#### 🏔️ 地形数据")
    uploaded_dem = st.file_uploader("Upload DEM (.tif)", type=['tif', 'tiff'])
    if uploaded_dem:
        st.success("DEM Ready. Click 👁️ on any card.")
        
    st.divider()
    
    # 筛选器
    cats = sorted(list(set(r.get('category', '其他') for r in all_ramps)))
    # 韦斯安德森置顶
    if "韦斯·安德森" in cats:
        cats.remove("韦斯·安德森")
        cats.insert(0, "韦斯·安德森")
        
    sel_cat = st.selectbox("Category", ["All"] + cats)
    search = st.text_input("Search", placeholder="Type to filter...")
    
    st.divider()
    
    # 导出功能
    if st.session_state.selected_ramps:
        st.markdown(f"**Export ({len(st.session_state.selected_ramps)})**")
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button("Download JSON Bundle", json.dumps(export_data, indent=2, ensure_ascii=False), "colors.json", "application/json", type="primary")

# --- 主界面 ---

st.title("Color Library.")
st.caption("Cinematic & Scientific Color Ramps for ArcGIS.")
st.write("")

# === 🌟 优化的可视化舞台 ===
if st.session_state.preview_colors and uploaded_dem:
    st.markdown('<div class="viz-stage">', unsafe_allow_html=True)
    st.markdown(f'<div class="viz-header">PREVIEWING: {st.session_state.preview_name}</div>', unsafe_allow_html=True)
    
    # 渲染逻辑
    with st.spinner("Rendering High-Res Map..."):
        try:
            fig = plot_dem_optimized(uploaded_dem, st.session_state.preview_colors)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        except Exception as e:
            st.error(f"渲染失败: {e}")
            
    # 关闭预览按钮
    if st.button("Close Preview", type="secondary"):
        st.session_state.preview_colors = None
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)
elif st.session_state.preview_colors and not uploaded_dem:
    st.info("👆 Please upload a DEM file in the sidebar to see the visualization.")

# === 色带列表 ===

# 筛选逻辑
filtered = all_ramps
if sel_cat != "All":
    filtered = [r for r in filtered if r.get('category', '其他') == sel_cat]
if search:
    s = search.lower()
    filtered = [r for r in filtered if s in r['name'].lower()]

if not filtered:
    st.warning("No color ramps found.")
else:
    # 4列布局
    cols = st.columns(4)
    for idx, ramp in enumerate(filtered):
        with cols[idx % 4]:
            st.markdown(f"""
            <div class="apple-card">
                <div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div>
                <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 按钮控制区：更紧凑
            # 第一行：预览 | 加入
            r1_c1, r1_c2 = st.columns(2)
            name = ramp['name']
            
            with r1_c1:
                st.button("👁️ 渲染", key=f"viz_{idx}", on_click=set_preview, args=(name, ramp['colors']))
            
            with r1_c2:
                if name in st.session_state.selected_ramps:
                    st.button("✓ 已选", key=f"sel_{idx}", on_click=toggle_ramp_select, args=(name,), type="secondary")
                else:
                    st.button("＋ 加入", key=f"sel_{idx}", on_click=toggle_ramp_select, args=(name,))
            
            # 第二行：下载 | 删除 (红色)
            r2_c1, r2_c2 = st.columns(2)
            
            with r2_c1:
                st.download_button("⬇ CLR", generate_clr(ramp['colors']), file_name=f"{name}.clr", key=f"dl_{idx}")
            
            with r2_c2:
                # 红色删除按钮 (使用 type='primary' 配合 CSS 变红)
                st.button("🗑️ 删除", key=f"del_{idx}", on_click=delete_ramp_permanent, args=(name,), type="primary")
            
            st.write("") # 底部留白import streamlit as st
import json
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ==========================================
# 1. 核心配置 & CSS 样式优化
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio Pro",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全局字体 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    /* 右侧预览区固定面板样式 */
    .preview-panel {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        position: sticky;
        top: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
    }
    
    /* 卡片样式优化 */
    .color-card {
        background: white;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #f0f0f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        transition: all 0.2s;
    }
    .color-card:hover {
        border-color: #007AFF;
        box-shadow: 0 4px 8px rgba(0,122,255,0.1);
    }
    
    /* 渐变条 */
    .gradient-bar {
        height: 40px;
        width: 100%;
        border-radius: 6px;
        margin-bottom: 8px;
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* 标题 */
    .card-title {
        font-size: 12px;
        font-weight: 600;
        color: #333;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        margin-bottom: 6px;
    }
    
    /* 按钮微调 */
    .stButton button {
        border-radius: 6px;
        font-size: 11px;
        padding: 2px 10px;
        height: auto;
    }
    
    /* 隐藏顶部Padding */
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑函数
# ==========================================

# --- 数据 IO 操作 (含删除) ---
FILE_PATH = 'palettes.json'

@st.cache_data
def load_data():
    if not os.path.exists(FILE_PATH): return []
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 展平嵌套列表
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                return [item for sublist in data for item in sublist]
            return data
    except: return []

def save_data(data):
    """将数据写回 JSON 文件"""
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def delete_ramp_by_name(name_to_delete):
    """物理删除色带"""
    current_data = load_data() # 获取最新数据
    # 过滤掉要删除的
    new_data = [r for r in current_data if r['name'] != name_to_delete]
    
    # 写回文件
    save_data(new_data)
    
    # 清除缓存并刷新
    load_data.clear()
    
    # 如果当前选中的也是这个，从session移除
    if name_to_delete in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name_to_delete)
    
    st.toast(f"已永久删除: {name_to_delete}")
    st.rerun()

# --- 辅助函数 ---
def init_session():
    if 'selected_ramps' not in st.session_state: st.session_state.selected_ramps = []
    if 'preview_colors' not in st.session_state: st.session_state.preview_colors = None
    if 'preview_name' not in st.session_state: st.session_state.preview_name = None

def toggle_select(name):
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

def set_preview(name, colors):
    st.session_state.preview_name = name
    st.session_state.preview_colors = colors

def hex_to_rgb(hex_code):
    try:
        h = hex_code.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return (0,0,0)

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

# --- 绘图引擎 (高清优化版) ---
def plot_dem_high_res(dem_file, colors):
    with rasterio.open(dem_file) as src:
        # 你的DEM大概40MB，我们可以适当放宽限制，保证清晰度
        # 限制最大边长为 1500px，这样既清晰又不会爆内存
        max_dim = 1500  
        scale = min(1.0, max_dim / max(src.width, src.height))
        
        if scale < 1.0:
            new_h = int(src.height * scale)
            new_w = int(src.width * scale)
            data = src.read(1, out_shape=(new_h, new_w), resampling=rasterio.enums.Resampling.bilinear)
        else:
            data = src.read(1)
            
        data = data.astype('float32')
        if src.nodata is not None:
            data[data == src.nodata] = np.nan

    cmap = LinearSegmentedColormap.from_list("custom", colors)
    
    # 优化绘图参数：去除白边，提高DPI
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150) # 尺寸调小，DPI调高
    ax.axis('off')
    # 使用 aspect='equal' 保持地理比例
    ax.imshow(data, cmap=cmap, aspect='equal')
    
    # 移除所有边距
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0,0)
    
    return fig

# ==========================================
# 3. 页面布局
# ==========================================
init_session()
all_ramps = load_data()

# --- 侧边栏: 上传与导出 ---
with st.sidebar:
    st.title("🗺️ 地理数据")
    uploaded_dem = st.file_uploader("上传 DEM (TIF)", type=['tif', 'tiff'])
    if uploaded_dem:
        st.success("DEM 已就绪")
    else:
        st.caption("上传后可预览地形渲染效果")
        
    st.divider()
    
    st.title("📦 导出管理")
    if st.session_state.selected_ramps:
        st.write(f"已选: {len(st.session_state.selected_ramps)} 个")
        export_list = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button("下载 JSON 配置包", json.dumps(export_list, indent=2, ensure_ascii=False), "gis_colors.json", "application/json", type="primary")
    else:
        st.caption("暂未选择色带")

# --- 主界面：分栏布局 ---
# 左侧(70%)：色带列表 | 右侧(30%)：固定预览图
col_list, col_preview = st.columns([7, 3]) 

# === 右侧：可视化预览面板 (Sticky Layout) ===
with col_preview:
    st.markdown('<div class="preview-panel">', unsafe_allow_html=True)
    st.markdown("### 🌏 效果预览")
    
    if st.session_state.preview_colors:
        st.markdown(f"**{st.session_state.preview_name}**")
        
        # 渲染区域
        if uploaded_dem:
            with st.spinner("渲染中..."):
                fig = plot_dem_high_res(uploaded_dem, st.session_state.preview_colors)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
        else:
            # 如果没传DEM，显示一个简单的渐变条作为替代
            grad_css = f"linear-gradient(to right, {', '.join(st.session_state.preview_colors)})"
            st.markdown(f'<div style="width:100%; height:150px; background:{grad_css}; border-radius:8px;"></div>', unsafe_allow_html=True)
            st.info("上传 DEM 文件可查看真实地形效果")
            
    else:
        st.markdown("""
        <div style="height:200px; display:flex; align-items:center; justify-content:center; color:#ccc; border:2px dashed #eee; border-radius:8px;">
            点击左侧 👁️ 图标预览
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# === 左侧：色带列表 ===
with col_list:
    # 顶部筛选工具
    c_cat, c_search = st.columns([1, 2])
    with c_cat:
        cats = ["全部"] + sorted(list(set(r.get('category', '其他') for r in all_ramps)))
        sel_cat = st.selectbox("分类筛选", cats, label_visibility="collapsed")
    with c_search:
        search_txt = st.text_input("搜索色带", placeholder="输入名称...", label_visibility="collapsed")
    
    # 过滤数据
    filtered = all_ramps
    if sel_cat != "全部": filtered = [r for r in filtered if r.get('category', '其他') == sel_cat]
    if search_txt: filtered = [r for r in filtered if search_txt.lower() in r['name'].lower()]

    st.markdown("---")
    
    if not filtered:
        st.warning("未找到数据")
    else:
        # 3列布局展示卡片
        grid_cols = st.columns(3)
        for idx, ramp in enumerate(filtered):
            with grid_cols[idx % 3]:
                # 卡片 HTML
                st.markdown(f"""
                <div class="color-card">
                    <div class="gradient-bar" style="background: linear-gradient(to right, {', '.join(ramp['colors'])});"></div>
                    <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 功能按钮区
                b1, b2, b3, b4 = st.columns([1, 1, 1, 1], gap="small")
                
                name = ramp['name']
                
                # 1. 预览 (👁️)
                with b1:
                    st.button("👁️", key=f"v_{idx}", on_click=set_preview, args=(name, ramp['colors']), help="在右侧地图预览", use_container_width=True)
                
                # 2. 下载 (⬇)
                with b2:
                    st.download_button("⬇", data=generate_clr(ramp['colors']), file_name=f"{name}.clr", key=f"d_{idx}", help="下载CLR文件", use_container_width=True)
                
                # 3. 选中 (✓)
                with b3:
                    is_in = name in st.session_state.selected_ramps
                    btn_label = "✓" if is_in else "＋"
                    btn_type = "primary" if is_in else "secondary"
                    st.button(btn_label, key=f"s_{idx}", on_click=toggle_select, args=(name,), type=btn_type, help="加入导出列表", use_container_width=True)

                # 4. 删除 (🗑️) - 红色按钮
                with b4:
                    # 使用回调直接删除，无需二次确认(为了快捷)，如果需要确认可以使用 st.popover
                    st.button("🗑️", key=f"del_{idx}", on_click=delete_ramp_by_name, args=(name,), type="primary", help="永久删除此色带", use_container_width=True)
