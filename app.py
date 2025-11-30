import streamlit as st
import json
import os

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
        box-shadow: inset 0 0 0 1px rgba(0,0,0,0.03); /* 内描边，增加质感 */
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
        color: #0071E3 !important; /* Apple Blue */
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
    
    /* 选中状态按钮 */
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #E8F2FF !important;
        color: #0071E3 !important;
        border-color: transparent !important;
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
    
    /* 隐藏 Streamlit 默认头部 */
    header[data-testid="stHeader"] {background: transparent;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 逻辑处理
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

@st.cache_data
def load_data():
    """带错误诊断的数据加载"""
    file_path = 'palettes.json'
    if not os.path.exists(file_path):
        return [], None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 兼容性处理：如果是嵌套列表 [[...]]，则展平
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                flat_data = []
                for sublist in data:
                    flat_data.extend(sublist)
                data = flat_data
            return data, None
    except json.JSONDecodeError as e:
        # 捕获具体错误行内容
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        error_context = "无法读取上下文"
        if 0 <= e.lineno - 1 < len(lines):
            error_context = lines[e.lineno - 1].strip()
        
        error_msg = {
            "msg": e.msg,
            "line": e.lineno,
            "col": e.colno,
            "context": error_context
        }
        return [], error_msg
    except Exception as e:
        return [], {"msg": str(e), "line": 0, "col": 0, "context": "未知错误"}

# ==========================================
# 3. 页面渲染
# ==========================================
init_session()
all_ramps, error_info = load_data()

# --- 错误处理 UI ---
if error_info:
    st.error("❌ 数据文件 (palettes.json) 格式有误，请检查！")
    with st.expander("点击查看错误详情 (诊断模式)", expanded=True):
        st.markdown(f"**错误原因**: `{error_info['msg']}`")
        st.markdown(f"**出错位置**: 第 `{error_info['line']}` 行")
        st.markdown("**问题代码片段**:")
        st.code(error_info['context'], language="json")
        st.info("💡 提示：如果是 'Expecting ',' delimiter'，通常意味着这一行的上一行末尾少了一个逗号 `,`，或者这一行缺少逗号。")
    st.stop() # 停止渲染其余部分

# --- 正常渲染 ---
all_names = [r['name'] for r in all_ramps]
valid_selections = [n for n in st.session_state.selected_ramps if n in all_names]
st.session_state.selected_ramps = valid_selections

# 侧边栏
with st.sidebar:
    st.markdown("###  Color Studio")
    
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
        st.caption(f"已选 {len(st.session_state.selected_ramps)} 项")
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button(
            "导出 JSON 配置包",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name="gis_colors.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )
    else:
        st.button("导出 (空)", disabled=True, use_container_width=True)

# 主界面 Hero
st.markdown('<div class="hero-title">Color Library.</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Cinematic & Scientific palettes for ArcGIS Pro.</div>', unsafe_allow_html=True)

# 快速添加栏
if all_names:
    st.multiselect(
        "Quick Add:",
        options=all_names,
        default=st.session_state.selected_ramps,
        key="ms_widget",
        on_change=sync_multiselect,
        placeholder="搜索并添加到导出列表...",
        label_visibility="collapsed"
    )
st.write("")

# 筛选
filtered = all_ramps
if sel_cat != "全部":
    filtered = [r for r in filtered if r.get('category', '其他') == sel_cat]
if search:
    s = search.lower()
    filtered = [r for r in filtered if s in r['name'].lower()]

# 网格展示
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
            
            c1, c2 = st.columns([1, 1])
            name = ramp['name']
            is_sel = name in st.session_state.selected_ramps
            
            with c1:
                if is_sel:
                    st.button("Remove", key=f"r_{idx}", on_click=toggle_ramp, args=(name,), type="secondary", use_container_width=True)
                else:
                    st.button("Add", key=f"a_{idx}", on_click=toggle_ramp, args=(name,), use_container_width=True)
            with c2:
                st.download_button("CLR", data=generate_clr(ramp['colors']), file_name=f"{name}.clr", key=f"d_{idx}", use_container_width=True)
            st.write("")
