import streamlit as st
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
