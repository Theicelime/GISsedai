import streamlit as st
import json
import os

# --------------------------------------------------------
# 1. 页面配置
# --------------------------------------------------------
st.set_page_config(
    page_title="GIS Color Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------
# 2. 辅助函数
# --------------------------------------------------------
@st.cache_data
def load_data():
    """读取本地 JSON 数据库"""
    try:
        if os.path.exists('palettes.json'):
            with open('palettes.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        else:
            return []
    except Exception as e:
        st.error(f"数据加载失败: {e}")
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

# --------------------------------------------------------
# 3. 初始化状态与数据
# --------------------------------------------------------
if 'selected_ramps' not in st.session_state:
    st.session_state.selected_ramps = []

# 加载全量数据
all_ramps = load_data()
all_ramp_names = [r['name'] for r in all_ramps]

# --------------------------------------------------------
# 4. 侧边栏：筛选器
# --------------------------------------------------------
st.sidebar.title("🎬 GIS Color Studio")
st.sidebar.caption("电影级 · 空间色彩美学")

categories = ["全部"] + sorted(list(set(r.get('category', 'Uncategorized') for r in all_ramps)))
selected_cat = st.sidebar.selectbox("分类筛选", categories)
search_term = st.sidebar.text_input("搜索 (名称/色系)", "")

# 过滤数据 (仅用于卡片展示)
filtered_ramps = all_ramps
if selected_cat != "全部":
    filtered_ramps = [r for r in filtered_ramps if r.get('category') == selected_cat]
if search_term:
    term = search_term.lower()
    filtered_ramps = [r for r in filtered_ramps if term in r['name'].lower() or any(term in t.lower() for t in r.get('tags', []))]

st.sidebar.divider()
st.sidebar.metric("当前展示", len(filtered_ramps))

# --------------------------------------------------------
# 5. 主界面：导出管理器 (Export Manager)
# --------------------------------------------------------
st.title("色彩资产库")

# 使用容器包裹顶部管理器
with st.container():
    st.info("💡 提示：点击下方色带卡片中的按钮，即可加入/移除待导出列表。")
    
    # 修复核心 Bug：Multiselect 的 options 必须包含所有可能的值
    # 我们使用 all_ramp_names 而不是 filtered_ramps 的名字
    selected_from_multiselect = st.multiselect(
        "📦 待导出清单 (已选色带):",
        options=all_ramp_names,
        default=st.session_state.selected_ramps,
        key="global_multiselect"
    )

    # 状态同步逻辑：如果用户在多选框里删除了某项，需要更新 session state
    if selected_from_multiselect != st.session_state.selected_ramps:
        st.session_state.selected_ramps = selected_from_multiselect
        st.rerun()

    # 下载按钮
    if st.session_state.selected_ramps:
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        json_str = json.dumps(export_data, indent=2)
        
        col_dl_1, col_dl_2 = st.columns([1, 5])
        with col_dl_1:
            st.download_button(
                label=f"⬇️ 下载数据包 ({len(export_data)}个)",
                data=json_str,
                file_name="selected_colors.json",
                mime="application/json",
                type="primary"
            )
        with col_dl_2:
            if st.button("清空选择"):
                st.session_state.selected_ramps = []
                st.rerun()

# --------------------------------------------------------
# 6. 色带网格展示 (Grid Display)
# --------------------------------------------------------
st.divider()

if not filtered_ramps:
    st.warning("没有找到匹配的色带。")
else:
    # 3列布局
    cols = st.columns(3)
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 3]:
            # CSS 卡片样式
            st.markdown(f"""
            <div style="
                border:1px solid #e0e0e0; 
                border-radius:8px; 
                padding:12px; 
                margin-bottom:8px; 
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="
                    height: 45px; 
                    width: 100%; 
                    background: {generate_css_gradient(ramp['colors'])}; 
                    border-radius: 4px;
                    margin-bottom: 8px;">
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h5 style="margin:0; font-size:14px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{ramp['name']}</h5>
                    <span style="font-size:10px; background:#f0f2f6; padding:2px 6px; border-radius:4px;">{len(ramp['colors'])} C</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 按钮区域
            btn_col1, btn_col2 = st.columns([1, 1])
            
            # 1. 交互式选择按钮 (Click to Select)
            is_selected = ramp['name'] in st.session_state.selected_ramps
            
            if is_selected:
                if btn_col1.button("✅ 已选", key=f"btn_remove_{idx}", type="secondary", use_container_width=True):
                    st.session_state.selected_ramps.remove(ramp['name'])
                    st.rerun()
            else:
                if btn_col1.button("➕ 加入", key=f"btn_add_{idx}", type="primary", use_container_width=True):
                    st.session_state.selected_ramps.append(ramp['name'])
                    st.rerun()

            # 2. 单文件下载按钮
            clr_data = generate_clr(ramp['colors'])
            btn_col2.download_button(
                "下载 CLR", 
                clr_data, 
                file_name=f"{ramp['name'].replace(' ', '_')}.clr", 
                key=f"dl_clr_{idx}",
                use_container_width=True
            )
            
            # 标签展示
            st.markdown(f"""
            <div style="margin-bottom:20px; font-size:11px; color:#888;">
                 {' · '.join(ramp.get('tags', [])[:3])}
            </div>
            """, unsafe_allow_html=True)
