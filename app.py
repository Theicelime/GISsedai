import streamlit as st
import json
import os

# ==========================================
# 1. 页面配置 & 核心 CSS 注入 (Apple Style)
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 Apple 风格 CSS
st.markdown("""
<style>
    /* 1. 字体与全局背景 - 使用系统字体栈模拟 Apple 渲染 */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #F5F5F7; /* Apple 浅灰背景 */
        color: #1D1D1F;
    }
    
    /* 2. 侧边栏优化 - 模拟 iPad 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px); /* 毛玻璃效果 */
        border-right: 1px solid rgba(0,0,0,0.05);
    }
    
    /* 3. 卡片样式 - 核心设计元素 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 18px; /* 大圆角 */
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid rgba(0,0,0,0.04);
        box-shadow: 0 4px 12px rgba(0,0,0,0.02); /* 极轻微的阴影 */
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        position: relative;
        overflow: hidden;
    }
    
    .apple-card:hover {
        transform: translateY(-4px) scale(1.005);
        box-shadow: 0 12px 24px rgba(0,0,0,0.06); /* 悬浮加深阴影 */
    }

    /* 4. 颜色条 - 圆润且平滑 */
    .gradient-bar {
        height: 50px;
        width: 100%;
        border-radius: 10px;
        margin-bottom: 14px;
        /* 内部阴影增加质感 */
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05);
    }

    /* 5. 文字排版 */
    .card-title {
        font-size: 15px;
        font-weight: 600;
        color: #1D1D1F;
        letter-spacing: -0.01em;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .card-subtitle {
        font-size: 11px;
        color: #86868B; /* Apple 经典的次级文本灰 */
        font-weight: 500;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
    }

    /* 6. 按钮重塑 - 模拟 iOS 按钮 */
    /* 覆盖 Streamlit 默认按钮样式 */
    div.stButton > button {
        border-radius: 980px !important; /* 胶囊形状 */
        border: none !important;
        background-color: #F5F5F7 !important;
        color: #0071E3 !important; /* Apple Blue */
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 4px 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    
    div.stButton > button:hover {
        background-color: #0071E3 !important;
        color: white !important;
    }
    
    div.stButton > button:active {
        transform: scale(0.96);
    }

    /* 特定状态按钮：已选中的样式 */
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #E8F2FF !important;
        color: #0071E3 !important;
    }

    /* 顶部 Hero 区域文字 */
    .hero-title {
        font-size: 48px;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #1D1D1F;
    }
    .hero-sub {
        font-size: 24px;
        color: #86868B;
        font-weight: 400;
        margin-bottom: 40px;
    }
    
    /* 隐藏 Streamlit 默认头部 */
    header[data-testid="stHeader"] {
        background: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑层 (保持不变，确保稳定性)
# ==========================================
def init_session():
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []

def toggle_ramp(name):
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

def sync_multiselect():
    st.session_state.selected_ramps = st.session_state.ms_widget

@st.cache_data
def load_data():
    all_data = []
    if os.path.exists('palettes.json'):
        try:
            with open('palettes.json', 'r', encoding='utf-8') as f:
                all_data.extend(json.load(f))
        except: pass
    
    # 去重
    seen = set()
    unique_data = []
    for item in all_data:
        if item['name'] not in seen:
            unique_data.append(item)
            seen.add(item['name'])
    return unique_data

def hex_to_rgb(hex_code):
    h = hex_code.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def get_gradient_css(colors):
    return f"linear-gradient(to right, {', '.join(colors)})"

# ==========================================
# 3. 页面渲染 (Apple Layout)
# ==========================================
init_session()
all_ramps = load_data()
all_names = [r['name'] for r in all_ramps]

# --- 侧边栏 (极简风格) ---
with st.sidebar:
    st.markdown("###  GIS Color Studio")
    st.write("") # Spacer
    
    # 分类筛选
    cats = ["全部"] + sorted(list(set(r.get('category', '未分类') for r in all_ramps)))
    # 强制让 "韦斯·安德森" 排在前面方便查找
    if "韦斯·安德森" in cats:
        cats.remove("韦斯·安德森")
        cats.insert(1, "韦斯·安德森")
        
    sel_cat = st.selectbox("浏览分类", cats)
    search = st.text_input("搜索", placeholder="Search...")
    
    st.divider()
    
    # 导出区域 (Sidebar 底部)
    st.markdown("#### 导出管理")
    if st.session_state.selected_ramps:
        st.caption(f"已选择 {len(st.session_state.selected_ramps)} 个色带")
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button(
            "下载 JSON 配置包",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name="gis_colors.json",
            mime="application/json",
            type="primary", # 会显示为主色调
            use_container_width=True
        )
    else:
        st.caption("暂未选择任何色带")
        st.button("下载 (空)", disabled=True, use_container_width=True)

# --- 主内容区 (Hero Header) ---
st.markdown('<div class="hero-title">GIS Color Studio.</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Pro-grade cinematic palettes for ArcGIS & QGIS.</div>', unsafe_allow_html=True)

# 确保状态同步
valid_selections = [n for n in st.session_state.selected_ramps if n in all_names]
st.session_state.selected_ramps = valid_selections

# 快速选择栏 (顶部悬浮感)
with st.container():
    st.multiselect(
        "Add to Library:",
        options=all_names,
        default=st.session_state.selected_ramps,
        key="ms_widget",
        on_change=sync_multiselect,
        placeholder="Search for movies, styles..."
    )

st.write("") # Spacer

# --- 筛选逻辑 ---
filtered = all_ramps
if sel_cat != "全部":
    filtered = [r for r in filtered if r.get('category') == sel_cat]
if search:
    s = search.lower()
    filtered = [r for r in filtered if s in r['name'].lower() or any(s in t.lower() for t in r.get('tags', []))]

# --- 网格展示 (Grid) ---
if not filtered:
    st.warning("No palettes found.")
else:
    # 4 列布局，更加开阔
    cols = st.columns(4)
    
    for idx, ramp in enumerate(filtered):
        with cols[idx % 4]:
            
            # 卡片主体 (HTML)
            st.markdown(f"""
            <div class="apple-card">
                <div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div>
                <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
                <div class="card-subtitle">
                    <span>{ramp.get('category')}</span>
                    <span>{len(ramp['colors'])} Colors</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 按钮组 (独立于 Card div，利用 Streamlit 的布局)
            # 使用 container 模拟卡片底部的操作区
            c_btn1, c_btn2 = st.columns([1, 1])
            
            name = ramp['name']
            is_in = name in st.session_state.selected_ramps
            
            with c_btn1:
                # 根据状态改变按钮文字和样式
                if is_in:
                    st.button("Remove", key=f"rem_{idx}", on_click=toggle_ramp, args=(name,), use_container_width=True, type="secondary")
                else:
                    st.button("Add", key=f"add_{idx}", on_click=toggle_ramp, args=(name,), use_container_width=True)
            
            with c_btn2:
                st.download_button(
                    "CLR",
                    data=generate_clr(ramp['colors']),
                    file_name=f"{name.replace(' ', '_')}.clr",
                    key=f"dl_{idx}",
                    use_container_width=True
                )
            
            # 增加底部间距
            st.write("") 
            st.write("")
