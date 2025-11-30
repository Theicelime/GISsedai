import streamlit as st
import json
import os

# ==========================================
# 1. 页面配置 & Apple 极简风格 CSS
# ==========================================
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全局重置：Apple 系统字体栈 */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
        background-color: #F5F5F7;
        color: #1D1D1F;
    }
    
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0,0,0,0.05);
    }

    /* 极简卡片 */
    .apple-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 10px;
        margin-bottom: 8px;
        border: 1px solid rgba(0,0,0,0.02);
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.2s;
    }
    
    .apple-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.08);
        border-color: rgba(0,0,0,0.05);
    }

    /* 色带条 */
    .gradient-bar {
        height: 60px;
        width: 100%;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.03);
    }

    /* 名称 */
    .card-title {
        font-size: 13px;
        font-weight: 500;
        color: #333;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        letter-spacing: -0.01em;
        margin-bottom: 2px;
    }

    /* 按钮美化 */
    div.stButton > button {
        border-radius: 20px !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        background-color: #FBFBFD !important;
        color: #0071E3 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 2px 10px !important;
        height: auto !important;
        min-height: 28px !important;
        box-shadow: none !important;
        transition: all 0.2s !important;
    }

    div.stButton > button:hover {
        background-color: #0071E3 !important;
        color: #fff !important;
        border-color: #0071E3 !important;
    }
    
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #E8F2FF !important;
        color: #0071E3 !important;
        border: 1px solid transparent !important;
    }

    /* Hero 文字 */
    .hero-title {
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #1D1D1F;
        margin-bottom: 4px;
    }
    .hero-sub {
        font-size: 16px;
        color: #86868B;
        font-weight: 400;
        margin-bottom: 24px;
    }
    
    header[data-testid="stHeader"] {background: transparent;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑处理 (带诊断功能)
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
    file_path = 'palettes.json'
    
    if not os.path.exists(file_path):
        st.error(f"❌ 错误：找不到文件 '{file_path}'。请确保文件在同一目录下。")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
            # 处理嵌套列表的情况 (防止用户直接把新数组粘贴到旧数组里变成 [[...],[...]])
            if isinstance(raw_data, list):
                for item in raw_data:
                    if isinstance(item, list):
                        all_data.extend(item) # 展平嵌套列表
                    else:
                        all_data.append(item)
            else:
                st.error("❌ JSON 格式错误：根节点必须是一个列表 [...]")
                return []

    except json.JSONDecodeError as e:
        st.error(f"❌ JSON 语法错误！请检查逗号、引号或括号。\n\n错误位置：第 {e.lineno} 行, 第 {e.colno} 列\n错误详情：{e.msg}")
        return []
    except Exception as e:
        st.error(f"❌ 未知错误：{e}")
        return []
    
    # 数据清洗与去重
    seen = set()
    unique_data = []
    valid_count = 0
    
    for item in all_data:
        # 确保是字典且有必要字段
        if isinstance(item, dict) and 'name' in item and 'colors' in item:
            valid_count += 1
            if item['name'] not in seen:
                unique_data.append(item)
                seen.add(item['name'])
    
    if valid_count == 0:
        st.warning("⚠️ JSON 文件读取成功，但没有发现有效的色带数据。请检查 key 是否为 'name' 和 'colors'。")

    return unique_data

def hex_to_rgb(hex_code):
    try:
        h = hex_code.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (0,0,0) # 防止颜色代码错误导致崩溃

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def get_gradient_css(colors):
    return f"linear-gradient(to right, {', '.join(colors)})"

# ==========================================
# 3. 页面渲染
# ==========================================
init_session()
all_ramps = load_data()
all_names = [r['name'] for r in all_ramps]

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("###  Color Studio")
    
    if all_ramps:
        # 动态提取分类
        unique_categories = set(r.get('category', 'Other') for r in all_ramps)
        sorted_cats = sorted(list(unique_categories))
        
        # 韦斯·安德森置顶
        if "韦斯·安德森" in sorted_cats:
            sorted_cats.remove("韦斯·安德森")
            sorted_cats.insert(0, "韦斯·安德森")
            
        cats_display = ["全部"] + sorted_cats
        
        sel_cat = st.selectbox("分类", cats_display)
        search = st.text_input("搜索", placeholder="Search...")
        
        st.divider()
        
        # 导出模块
        if st.session_state.selected_ramps:
            st.caption(f"已选 {len(st.session_state.selected_ramps)} 项")
            export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
            st.download_button(
                "导出 JSON",
                data=json.dumps(export_data, indent=2, ensure_ascii=False),
                file_name="gis_colors.json",
                mime="application/json",
                type="primary",
                use_container_width=True
            )
        else:
            st.button("导出 (空)", disabled=True, use_container_width=True)
    else:
        st.error("无法加载侧边栏：数据为空")

# --- 主界面 ---
valid_selections = [n for n in st.session_state.selected_ramps if n in all_names]
st.session_state.selected_ramps = valid_selections

st.markdown('<div class="hero-title">Library.</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Cinematic color palettes for cartography.</div>', unsafe_allow_html=True)

# 搜索栏 (Quick Add)
if all_names:
    st.multiselect(
        "Quick Add:",
        options=all_names,
        default=st.session_state.selected_ramps,
        key="ms_widget",
        on_change=sync_multiselect,
        placeholder="Search and add...",
        label_visibility="collapsed"
    )
st.write("") 

# --- 筛选与展示 ---
if not all_ramps:
    st.markdown("### 🛠️ 数据加载失败，请检查 json 文件")
else:
    filtered = all_ramps
    if sel_cat != "全部":
        filtered = [r for r in filtered if r.get('category', 'Other') == sel_cat]
    if search:
        s = search.lower()
        filtered = [r for r in filtered if s in r['name'].lower() or any(s in t.lower() for t in r.get('tags', []))]

    if not filtered:
        st.info("No palettes found.")
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
                
                c1, c2 = st.columns([1, 1])
                name = ramp['name']
                is_selected = name in st.session_state.selected_ramps
                
                with c1:
                    if is_selected:
                        st.button("Remove", key=f"btn_r_{idx}", on_click=toggle_ramp, args=(name,), type="secondary", use_container_width=True)
                    else:
                        st.button("Add", key=f"btn_a_{idx}", on_click=toggle_ramp, args=(name,), use_container_width=True)
                
                with c2:
                    st.download_button(
                        "CLR", 
                        data=generate_clr(ramp['colors']), 
                        file_name=f"{name}.clr", 
                        key=f"btn_d_{idx}", 
                        use_container_width=True
                    )
                st.write("")
