import streamlit as st
import json
import os

# ==========================================
# 1. 核心配置与样式注入 (美化关键)
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS 以实现更紧凑、漂亮的按钮和卡片布局
st.markdown("""
<style>
    /* 全局字体优化 */
    body {font-family: 'Segoe UI', sans-serif;}
    
    /* 卡片容器样式 */
    .color-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .color-card:hover {
        border-color: #b0b0b0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 颜色条样式 */
    .gradient-bar {
        height: 45px;
        width: 100%;
        border-radius: 6px;
        margin-bottom: 10px;
        border: 1px solid rgba(0,0,0,0.05);
    }

    /* 标题样式 */
    .card-title {
        font-weight: 600;
        font-size: 14px;
        color: #333;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 4px;
    }
    
    /* 标签样式 */
    .card-tags {
        font-size: 11px;
        color: #888;
        margin-bottom: 10px;
        height: 18px; /* 固定高度防止错位 */
        overflow: hidden;
    }

    /* 按钮容器微调 - 让Streamlit按钮变小 */
    div[data-testid="column"] button {
        padding: 0.25rem 0.5rem !important;
        font-size: 0.8rem !important;
        line-height: 1.2 !important;
        min-height: 0px !important;
        height: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑处理与状态管理 (修复Bug关键)
# ==========================================
def init_session():
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []

# 回调：点击加入/移除按钮
def toggle_ramp(name):
    if name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name)
    else:
        st.session_state.selected_ramps.append(name)

# 回调：多选框变更
def sync_multiselect():
    st.session_state.selected_ramps = st.session_state.ms_widget

@st.cache_data
def load_data():
    all_data = []
    # 读取主文件
    if os.path.exists('palettes.json'):
        try:
            with open('palettes.json', 'r', encoding='utf-8') as f:
                all_data.extend(json.load(f))
        except: pass
    
    # 简单去重
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
# 3. 页面渲染逻辑
# ==========================================
init_session()
all_ramps = load_data()
all_names = [r['name'] for r in all_ramps]

# --- 侧边栏 ---
st.sidebar.header("🎨 GIS Color Studio")
st.sidebar.caption("电影级 · 空间色彩美学")
st.sidebar.divider()

cats = ["全部"] + sorted(list(set(r.get('category', '未分类') for r in all_ramps)))
sel_cat = st.sidebar.selectbox("📂 分类", cats)
search = st.sidebar.text_input("🔍 搜索", placeholder="输入电影名或色系...")

# 筛选
filtered = all_ramps
if sel_cat != "全部":
    filtered = [r for r in filtered if r.get('category') == sel_cat]
if search:
    s = search.lower()
    filtered = [r for r in filtered if s in r['name'].lower() or any(s in t.lower() for t in r.get('tags', []))]

st.sidebar.divider()
st.sidebar.caption(f"展示: {len(filtered)} / 总计: {len(all_ramps)}")

# --- 顶部管理区 (防Bug: 过滤掉不存在的选项) ---
st.title("色彩资产库")

valid_selections = [n for n in st.session_state.selected_ramps if n in all_names]
st.session_state.selected_ramps = valid_selections # 自我修复状态

with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        st.multiselect(
            "📦 已选色带 (支持搜索添加):",
            options=all_names,
            default=st.session_state.selected_ramps,
            key="ms_widget",
            on_change=sync_multiselect,
            placeholder="点击卡片上的 '+' 号，或在这里搜索..."
        )
    with c2:
        st.write("") # 布局对齐
        if st.session_state.selected_ramps:
            export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
            st.download_button(
                "⬇️ 导出 JSON 包",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name="gis_colors_export.json",
                mime="application/json",
                type="primary",
                use_container_width=True
            )
        else:
            st.button("请先选择色带", disabled=True, use_container_width=True)

st.markdown("---")

# --- 网格展示区 ---
if not filtered:
    st.info("未找到相关色带。")
else:
    # 响应式布局：每行4个更美观
    cols = st.columns(4)
    
    for idx, ramp in enumerate(filtered):
        with cols[idx % 4]:
            # 1. 渲染卡片 HTML
            st.markdown(f"""
            <div class="color-card">
                <div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div>
                <div class="card-title" title="{ramp['name']}">{ramp['name']}</div>
                <div class="card-tags">{', '.join(ramp.get('tags', [])[:2])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. 渲染按钮组 (紧凑布局)
            btn_col1, btn_col2 = st.columns([1, 1])
            
            name = ramp['name']
            is_in = name in st.session_state.selected_ramps
            
            with btn_col1:
                # 状态切换按钮：这里使用回调，不会立刻刷新整个页面导致闪烁
                if is_in:
                    st.button(
                        "✅ 已选", 
                        key=f"rem_{idx}", 
                        on_click=toggle_ramp, 
                        args=(name,), 
                        use_container_width=True
                    )
                else:
                    st.button(
                        "➕ 加入", 
                        key=f"add_{idx}", 
                        on_click=toggle_ramp, 
                        args=(name,), 
                        type="secondary", # 使用次级样式，不抢视觉
                        use_container_width=True
                    )
            
            with btn_col2:
                # 单个 CLR 下载
                st.download_button(
                    "⬇ CLR",
                    data=generate_clr(ramp['colors']),
                    file_name=f"{name.replace(' ', '_')}.clr",
                    key=f"dl_{idx}",
                    use_container_width=True
                )
