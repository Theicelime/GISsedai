import streamlit as st
import json
import os

# ==========================================
# 1. 核心配置 & Apple 风格 CSS
# ==========================================
st.set_page_config(
    page_title="Color Library",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 引入更现代的字体栈 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    /* 全局重置 */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #F5F5F7; /* Apple Light Gray */
        color: #1D1D1F;
    }
    
    /* 侧边栏：毛玻璃效果 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(24px);
        border-right: 1px solid rgba(0,0,0,0.06);
    }
    
    /* 隐藏顶部默认红线 */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        padding-top: 2rem;
    }

    /* === 卡片设计 (核心) === */
    .apple-card {
        background: #FFFFFF;
        border-radius: 20px; /* 更圆润 */
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid rgba(0,0,0,0.04);
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); /* 极淡的阴影 */
        transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
        position: relative;
        overflow: hidden;
    }
    
    .apple-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.08); /* 悬停浮起 */
        border-color: rgba(0,0,0,0.08);
    }

    /* 色带预览条 */
    .gradient-bar {
        height: 60px;
        width: 100%;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); /* 内发光提升质感 */
    }

    /* 卡片标题 */
    .card-title {
        font-size: 14px;
        font-weight: 600;
        color: #1D1D1F;
        margin-bottom: 16px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        letter-spacing: -0.01em;
    }

    /* === 按钮重构 (iOS Pill Style) === */
    div.stButton > button {
        border-radius: 100px !important; /* 胶囊形状 */
        border: none !important;
        background-color: #F2F2F7 !important;
        color: #0071E3 !important; /* Apple Blue */
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 6px 16px !important;
        height: auto !important;
        min-height: 32px !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: all 0.15s ease;
    }

    div.stButton > button:hover {
        background-color: #E8E8ED !important;
        transform: scale(1.02);
    }

    /* 选中状态 (Secondary Button) -> 实心蓝 */
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #0071E3 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="column"] button[kind="secondary"]:hover {
        background-color: #0077ED !important;
    }

    /* 删除按钮 (Primary Button) -> 红色文字，悬停变红底 */
    div[data-testid="column"] button[kind="primary"] {
        background-color: transparent !important;
        color: #FF3B30 !important; /* Apple Red */
        border: 1px solid rgba(255, 59, 48, 0.2) !important;
    }
    div[data-testid="column"] button[kind="primary"]:hover {
        background-color: #FF3B30 !important;
        color: white !important;
        border-color: #FF3B30 !important;
    }

    /* 标题排版 */
    .hero-container {
        margin-bottom: 40px;
    }
    .hero-title {
        font-size: 40px;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #1D1D1F;
    }
    .hero-subtitle {
        font-size: 19px;
        color: #86868B;
        font-weight: 400;
        margin-top: 4px;
    }
    
    /* 搜索框美化 */
    div[data-testid="stTextInput"] input {
        border-radius: 12px !important;
        background-color: #FFFFFF !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #0071E3 !important;
        box-shadow: 0 0 0 2px rgba(0,113,227,0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑处理
# ==========================================
def init_session():
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []

def toggle_select(name):
    """切换选中状态"""
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

def delete_permanent(name_to_delete):
    """永久删除：读文件 -> 删条目 -> 写文件"""
    all_data, _ = load_data_raw()
    new_data = [r for r in all_data if r['name'] != name_to_delete]
    
    try:
        with open('palettes.json', 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        
        # 清理 session
        if name_to_delete in st.session_state.selected_ramps:
            st.session_state.selected_ramps.remove(name_to_delete)
        
        # 修复点：删除了 st.rerun()，因为 on_click 结束后会自动 rerun
            
    except Exception as e:
        st.error(f"无法删除: {e}")

def load_data_raw():
    """读取 JSON 数据"""
    file_path = 'palettes.json'
    if not os.path.exists(file_path):
        return [], None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 处理可能的嵌套列表
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                flat = []
                for sub in data: flat.extend(sub)
                data = flat
            return data, None
    except Exception as e:
        return [], str(e)

# --- 颜色处理工具 ---
def hex_to_rgb(hex_code):
    try:
        h = hex_code.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (0,0,0)

def generate_clr(colors):
    """生成 ArcGIS CLR 内容"""
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def get_gradient_css(colors):
    """CSS 线性渐变"""
    return f"linear-gradient(to right, {', '.join(colors)})"

# ==========================================
# 3. 页面渲染
# ==========================================
init_session()
all_ramps, error_msg = load_data_raw()

if error_msg:
    st.error(f"❌ 数据文件损坏: {error_msg}")
    st.stop()

# --- 侧边栏 (Filter & Export) ---
with st.sidebar:
    st.markdown("###  Library")
    
    # 1. 筛选区
    cats = sorted(list(set(r.get('category', '其他') for r in all_ramps)))
    # 韦斯安德森置顶
    if "韦斯·安德森" in cats:
        cats.remove("韦斯·安德森")
        cats.insert(0, "韦斯·安德森")
    
    selected_cat = st.selectbox("Category", ["All"] + cats)
    search_query = st.text_input("Search", placeholder="Movies, colors...")
    
    st.divider()
    
    # 2. 导出区
    count = len(st.session_state.selected_ramps)
    st.markdown(f"**Export List ({count})**")
    
    if count > 0:
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button(
            label="Download JSON Bundle",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name="gis_color_bundle.json",
            mime="application/json",
            type="primary", # 蓝色按钮
            use_container_width=True
        )
        if st.button("Clear Selection", use_container_width=True):
            st.session_state.selected_ramps = []
            st.rerun()
    else:
        st.caption("Select palettes to create a bundle.")

# --- 主界面 ---
st.markdown("""
<div class="hero-container">
    <div class="hero-title">Color Library.</div>
    <div class="hero-subtitle">Curated palettes for cinematic maps.</div>
</div>
""", unsafe_allow_html=True)

# 筛选逻辑
filtered_ramps = all_ramps
if selected_cat != "All":
    filtered_ramps = [r for r in filtered_ramps if r.get('category', '其他') == selected_cat]
if search_query:
    q = search_query.lower()
    filtered_ramps = [r for r in filtered_ramps if q in r['name'].lower()]

# 网格展示
if not filtered_ramps:
    st.warning("No palettes found matching your criteria.")
else:
    # 响应式布局：4 列
    cols = st.columns(4)
    
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 4]:
            # 1. 纯 HTML/CSS 渲染卡片视觉部分
            st.markdown(f"""
            <div class="apple-card">
                <div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div>
                <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. 按钮交互部分 (使用 Streamlit 原生组件以保证逻辑稳定)
            # 布局：第一行 [选择] [下载]，第二行 [删除]
            
            c1, c2 = st.columns(2)
            name = ramp['name']
            
            with c1:
                is_selected = name in st.session_state.selected_ramps
                # 状态切换：选中显示蓝色实心(secondary)，未选中显示灰色(default)
                btn_label = "✓ Added" if is_selected else "＋ Add"
                
                if st.button(btn_label, key=f"sel_{idx}", on_click=toggle_select, args=(name,), type="secondary" if is_selected else "secondary", use_container_width=True):
                    pass 

            with c2:
                st.download_button(
                    "⬇ CLR", 
                    data=generate_clr(ramp['colors']), 
                    file_name=f"{name}.clr", 
                    key=f"dl_{idx}",
                    use_container_width=True
                )
            
            # 删除按钮
            if st.button("Trash", key=f"del_{idx}", on_click=delete_permanent, args=(name,), type="primary", use_container_width=True):
                pass
            
            # 增加底部间距
            st.markdown("<div style='margin-bottom: 24px'></div>", unsafe_allow_html=True)
