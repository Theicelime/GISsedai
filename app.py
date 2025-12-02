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
            
        st.rerun()
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
            if isinstance(data, list) and len(data) > 0
