import streamlit as st
import json
import os

# --------------------------------------------------------
# 1. 页面基础配置 (必须是第一行)
# --------------------------------------------------------
st.set_page_config(
    page_title="GIS Color Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------------
# 2. 回调与逻辑处理 (解决点击无反应的核心)
# --------------------------------------------------------
def init_session_state():
    """初始化 Session State"""
    if 'selected_ramps' not in st.session_state:
        st.session_state.selected_ramps = []

def toggle_selection(ramp_name):
    """
    回调函数：处理按钮点击
    使用回调可以保证在页面重新渲染前更新状态，解决'点击没反应'的问题
    """
    if ramp_name in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(ramp_name)
    else:
        st.session_state.selected_ramps.append(ramp_name)

def update_from_multiselect():
    """回调函数：处理多选框的变化"""
    st.session_state.selected_ramps = st.session_state.ms_selected

@st.cache_data
def load_data():
    """加载数据"""
    try:
        # 优先读取合并后的 palettes.json
        if os.path.exists('palettes.json'):
            with open('palettes.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"数据加载错误: {e}")
        return []

def hex_to_rgb(hex_code):
    h = hex_code.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def generate_clr(colors):
    content = ""
    for idx, hex_code in enumerate(colors):
        r, g, b = hex_to_rgb(hex_code)
        content += f"{idx + 1} {r} {g} {b}\n"
    return content

def generate_gradient_style(colors):
    return f"background: linear-gradient(to right, {', '.join(colors)});"

# --------------------------------------------------------
# 3. 初始化与数据加载
# --------------------------------------------------------
init_session_state()
all_ramps = load_data()
all_names = [r['name'] for r in all_ramps]

# --------------------------------------------------------
# 4. 侧边栏设计 (过滤器)
# --------------------------------------------------------
st.sidebar.title("🎨 GIS Color Studio")
st.sidebar.caption("电影级 · 空间色彩美学")
st.sidebar.markdown("---")

# 提取分类
categories = ["全部"] + sorted(list(set(r.get('category', 'Other') for r in all_ramps)))
selected_cat = st.sidebar.selectbox("📂 分类筛选", categories)

# 搜索框
search_term = st.sidebar.text_input("🔍 搜索色带", placeholder="如: Dune, Blue, Sci-Fi")

# 筛选逻辑
filtered_ramps = all_ramps
if selected_cat != "全部":
    filtered_ramps = [r for r in filtered_ramps if r.get('category') == selected_cat]
if search_term:
    t = search_term.lower()
    filtered_ramps = [r for r in filtered_ramps if t in r['name'].lower() or any(t in tag.lower() for tag in r.get('tags', []))]

# 侧边栏统计
st.sidebar.markdown("---")
st.sidebar.metric("📚 当前展示", f"{len(filtered_ramps)}", delta_color="off")
st.sidebar.caption(f"总收录: {len(all_ramps)} 个色带")

# --------------------------------------------------------
# 5. 主界面：顶部管理栏 (购物车模式)
# --------------------------------------------------------
st.title("色彩资产库")

# 使用 expander 收纳顶部区域，保持界面整洁，默认展开
with st.expander("📦 批量导出管理器 (已选色带)", expanded=True):
    col_sel, col_act = st.columns([3, 1])
    
    with col_sel:
        # 多选框，绑定回调，实现双向同步
        st.multiselect(
            "当前选中的色带:",
            options=all_names,
            default=st.session_state.selected_ramps,
            key="ms_selected",
            on_change=update_from_multiselect,
            placeholder="在下方点击 '➕' 添加，或在此处直接搜索选择..."
        )
    
    with col_act:
        st.write("") # 占位，对齐
        st.write("") 
        if st.session_state.selected_ramps:
            # 准备导出数据
            export_list = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
            json_str = json.dumps(export_list, indent=2)
            
            st.download_button(
                label=f"⬇️ 下载 JSON 包 ({len(export_list)})",
                data=json_str,
                file_name="gis_color_package.json",
                mime="application/json",
                type="primary",
                use_container_width=True
            )
        else:
            st.button("请先选择色带", disabled=True, use_container_width=True)

# --------------------------------------------------------
# 6. 色带网格展示 (美化版)
# --------------------------------------------------------
st.markdown("---")

if not filtered_ramps:
    st.info("👋 没有找到匹配的色带，请尝试清除筛选条件。")
else:
    # 定义网格列数 (响应式体验：大屏4列，中屏3列)
    cols = st.columns(3) 
    
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 3]:
            # 1. 视觉卡片 (HTML/CSS)
            # 优化：更紧凑的 padding，圆角，阴影
            st.markdown(f"""
            <div style="
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 5px;
                background-color: white;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                transition: box-shadow 0.2s;
            ">
                <div style="
                    height: 40px;
                    width: 100%;
                    {generate_gradient_style(ramp['colors'])}
                    border-radius: 6px;
                    margin-bottom: 8px;
                "></div>
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    margin-bottom: 4px;
                ">
                    <span style="font-weight: 600; font-size: 14px; color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%;">
                        {ramp['name']}
                    </span>
                    <span style="font-size: 10px; background: #f3f4f6; color: #6b7280; padding: 2px 6px; border-radius: 4px;">
                        {len(ramp['colors'])} Colors
                    </span>
                </div>
                <div style="font-size: 11px; color: #9ca3af; margin-bottom: 8px;">
                    {', '.join(ramp.get('tags', [])[:3])}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 2. 操作按钮区 (紧凑布局)
            # 使用两列布局：左边是状态切换，右边是单文件下载
            b_col1, b_col2 = st.columns([1, 1], gap="small")
            
            is_selected = ramp['name'] in st.session_state.selected_ramps
            
            with b_col1:
                # 状态切换按钮：使用回调函数 on_click，这是解决"点击没反应"的关键
                if is_selected:
                    st.button(
                        "✅ 已加入", 
                        key=f"btn_rem_{idx}", 
                        on_click=toggle_selection, 
                        args=(ramp['name'],), # 传递参数
                        type="secondary",    # 灰色样式表示已选/取消
                        use_container_width=True
                    )
                else:
                    st.button(
                        "➕ 加入", 
                        key=f"btn_add_{idx}", 
                        on_click=toggle_selection, 
                        args=(ramp['name'],), # 传递参数
                        type="primary",      # 红色/主色样式表示强调
                        use_container_width=True
                    )
            
            with b_col2:
                # 单文件下载
                clr_data = generate_clr(ramp['colors'])
                st.download_button(
                    label="⬇ CLR",
                    data=clr_data,
                    file_name=f"{ramp['name'].replace(' ', '_')}.clr",
                    key=f"dl_{idx}",
                    help="下载单个 .clr 文件",
                    use_container_width=True
                )
            
            # 增加一点间距
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
