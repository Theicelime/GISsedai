import streamlit as st
import json
import os
import numpy as np

# 新增库
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ==========================================
# 1. 核心配置 & Apple 风格 CSS
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全局字体与背景 */
    body {
        font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
        background-color: #F5F5F7;
        color: #1D1D1F;
    }
    
    /* 侧边栏毛玻璃 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0,0,0,0.05);
    }

    /* 极简卡片 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 12px;
        margin-bottom: 12px;
        border: 1px solid rgba(0,0,0,0.02);
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .apple-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
    }

    /* 色带预览条 */
    .gradient-bar {
        height: 55px;
        width: 100%;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.03); 
    }

    /* 标题样式 */
    .card-title {
        font-size: 13px;
        font-weight: 500;
        color: #1D1D1F;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        letter-spacing: -0.01em;
    }

    /* 按钮美化：iOS 风格 */
    div.stButton > button {
        border-radius: 20px !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        background-color: #FBFBFD !important;
        color: #0071E3 !important; 
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 4px 12px !important;
        height: 28px !important;
        line-height: 1 !important;
        box-shadow: none !important;
    }

    div.stButton > button:hover {
        background-color: #0071E3 !important;
        color: #fff !important;
    }

    /* 顶部大标题 */
    .hero-title {
        font-size: 34px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #1D1D1F;
        margin-top: -20px;
    }
    .hero-sub {
        font-size: 17px;
        color: #86868B;
        font-weight: 400;
        margin-bottom: 30px;
    }
    
    /* 可视化预览区样式 */
    .viz-container {
        background: white;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 30px;
        text-align: center;
    }
    
    header[data-testid="stHeader"] {background: transparent;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑处理
# ==========================================
def init_session():
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []
    # 新增：用于存储当前预览的色带
    if 'preview_colors' not in st.session_state:
        st.session_state.preview_colors = None
    if 'preview_name' not in st.session_state:
        st.session_state.preview_name = None

def toggle_ramp(name):
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

# 新增：点击“渲染”按钮的回调
def set_preview(name, colors):
    st.session_state.preview_name = name
    st.session_state.preview_colors = colors

def sync_multiselect():
    st.session_state.selected_ramps = st.session_state.ms_widget

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

# 新增：DEM 绘图核心函数
def plot_dem(dem_file, colors):
    """
    读取 DEM 并应用颜色。
    为了网页性能，会自动降采样(Thumbnail)。
    """
    with rasterio.open(dem_file) as src:
        # 计算缩放比例，限制最大宽度为 800px，防止大文件卡死
        max_dim = 800
        scale = min(1.0, max_dim / max(src.width, src.height))
        
        if scale < 1.0:
            new_height = int(src.height * scale)
            new_width = int(src.width * scale)
            data = src.read(1, out_shape=(new_height, new_width), resampling=rasterio.enums.Resampling.bilinear)
        else:
            data = src.read(1)
            
        # 处理 NoData 值 (通常转为 NaN)
        data = data.astype('float32')
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
            
    # 创建 Matplotlib 色带
    cmap = LinearSegmentedColormap.from_list("custom_ramp", colors)
    
    # 绘图
    fig, ax = plt.subplots(figsize=(10, 6))
    # 隐藏坐标轴
    ax.axis('off')
    # 绘制图像，使用 aspect='auto' 或 'equal'
    im = ax.imshow(data, cmap=cmap, interpolation='nearest')
    plt.tight_layout(pad=0)
    return fig

@st.cache_data
def load_data():
    file_path = 'palettes.json'
    if not os.path.exists(file_path):
        return [], None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                flat_data = []
                for sublist in data:
                    flat_data.extend(sublist)
                data = flat_data
            return data, None
    except json.JSONDecodeError as e:
        return [], {"msg": e.msg, "line": e.lineno}
    except Exception as e:
        return [], {"msg": str(e), "line": 0}

# ==========================================
# 3. 页面渲染
# ==========================================
init_session()
all_ramps, error_info = load_data()

if error_info:
    st.error("❌ 数据文件错误")
    st.stop()

all_names = [r['name'] for r in all_ramps]
st.session_state.selected_ramps = [n for n in st.session_state.selected_ramps if n in all_names]

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("###  Color Studio")
    
    # DEM 上传区域 (新增)
    st.markdown("#### 🏔️ 地理可视化")
    uploaded_dem = st.file_uploader("上传 DEM (TIF格式)", type=['tif', 'tiff'])
    if uploaded_dem:
        st.caption("✅ DEM 已加载，点击右侧卡片上的 '👁️' 按钮即可渲染。")
    else:
        st.caption("上传高程数据，实时预览色带效果。")

    st.divider()

    # 原有筛选逻辑
    unique_categories = set(r.get('category', '其他') for r in all_ramps)
    sorted_cats = sorted(list(unique_categories))
    if "韦斯·安德森" in sorted_cats:
        sorted_cats.remove("韦斯·安德森")
        sorted_cats.insert(0, "韦斯·安德森")
    
    cats_display = ["全部"] + sorted_cats
    sel_cat = st.selectbox("分类", cats_display)
    search = st.text_input("搜索", placeholder="Search...")
    
    st.divider()
    
    if st.session_state.selected_ramps:
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button(
            "导出配置包 (JSON)",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name="gis_colors.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )

# --- 主界面 ---
st.markdown('<div class="hero-title">Color Library.</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Cinematic & Scientific palettes for ArcGIS Pro.</div>', unsafe_allow_html=True)

# === 🌟 可视化预览区 (核心新增功能) ===
if st.session_state.preview_colors:
    if uploaded_dem:
        st.markdown(f"#### 👁️ Preview: {st.session_state.preview_name}")
        with st.container():
            # 使用 spinner 防止绘图时界面卡顿
            with st.spinner(f"正在渲染 {st.session_state.preview_name} ..."):
                fig = plot_dem(uploaded_dem, st.session_state.preview_colors)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig) # 释放内存
    else:
        # 如果点了渲染但没传文件，给个提示
        st.warning("☝️ 请先在左侧侧边栏上传 DEM (TIF) 文件，才能进行地理可视化。")

st.divider()

# --- 筛选与列表 ---
filtered = all_ramps
if sel_cat != "全部":
    filtered = [r for r in filtered if r.get('category', '其他') == sel_cat]
if search:
    s = search.lower()
    filtered = [r for r in filtered if s in r['name'].lower()]

if not filtered:
    st.info("未找到相关色带。")
else:
    cols = st.columns(4)
    for idx, ramp in enumerate(filtered):
        with cols[idx % 4]:
            st.markdown(f"""
            <div class="apple-card">
                <div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div>
                <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 按钮布局：增加了一个可视化按钮
            c1, c2, c3 = st.columns([1, 1, 1], gap="small")
            
            name = ramp['name']
            
            # 1. 渲染按钮 (可视化)
            with c1:
                # 使用回调函数更新 session_state
                st.button("👁️", key=f"v_{idx}", help="在地图上预览", 
                          on_click=set_preview, args=(name, ramp['colors']), 
                          use_container_width=True)
            
            # 2. 加入/移除按钮
            with c2:
                is_sel = name in st.session_state.selected_ramps
                if is_sel:
                    st.button("✓", key=f"r_{idx}", help="从导出列表移除", 
                              on_click=toggle_ramp, args=(name,), 
                              type="secondary", use_container_width=True)
                else:
                    st.button("＋", key=f"a_{idx}", help="加入导出列表", 
                              on_click=toggle_ramp, args=(name,), 
                              use_container_width=True)
            
            # 3. 下载按钮
            with c3:
                st.download_button("⬇", data=generate_clr(ramp['colors']), 
                                   file_name=f"{name}.clr", key=f"d_{idx}", 
                                   help="下载 .clr", use_container_width=True)
            
            st.write("")
