import streamlit as st
import json
import os
from github import Github, GithubException # 需要 pip install PyGithub

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background-color: #F5F5F7; color: #1D1D1F; }
    section[data-testid="stSidebar"] { background-color: rgba(255, 255, 255, 0.8); backdrop-filter: blur(24px); border-right: 1px solid rgba(0,0,0,0.06); }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2rem; }
    .apple-card { background: #FFFFFF; border-radius: 20px; padding: 16px; margin-bottom: 16px; border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1); position: relative; overflow: hidden; }
    .apple-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.08); border-color: rgba(0,0,0,0.08); }
    .gradient-bar { height: 60px; width: 100%; border-radius: 12px; margin-bottom: 12px; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.05); }
    .card-title { font-size: 14px; font-weight: 600; color: #1D1D1F; margin-bottom: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: -0.01em; }
    div.stButton > button { border-radius: 100px !important; border: none !important; background-color: #F2F2F7 !important; color: #0071E3 !important; font-size: 12px !important; font-weight: 500 !important; padding: 6px 16px !important; height: auto !important; min-height: 32px !important; width: 100% !important; box-shadow: none !important; transition: all 0.15s ease; }
    div.stButton > button:hover { background-color: #E8E8ED !important; transform: scale(1.02); }
    div[data-testid="column"] button[kind="secondary"] { background-color: #0071E3 !important; color: #FFFFFF !important; }
    div[data-testid="column"] button[kind="secondary"]:hover { background-color: #0077ED !important; }
    div[data-testid="column"] button[kind="primary"] { background-color: transparent !important; color: #FF3B30 !important; border: 1px solid rgba(255, 59, 48, 0.2) !important; }
    div[data-testid="column"] button[kind="primary"]:hover { background-color: #FF3B30 !important; color: white !important; border-color: #FF3B30 !important; }
    .hero-container { margin-bottom: 40px; }
    .hero-title { font-size: 40px; font-weight: 700; letter-spacing: -0.03em; color: #1D1D1F; }
    .hero-subtitle { font-size: 19px; color: #86868B; font-weight: 400; margin-top: 4px; }
    div[data-testid="stTextInput"] input { border-radius: 12px !important; background-color: #FFFFFF !important; border: 1px solid rgba(0,0,0,0.1) !important; }
    div[data-testid="stTextInput"] input:focus { border-color: #0071E3 !important; box-shadow: 0 0 0 2px rgba(0,113,227,0.2) !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑处理 (含 GitHub 同步)
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

def update_github_file(new_data):
    """
    通过 GitHub API 更新文件
    """
    try:
        # 1. 获取 Secrets 配置
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["REPO_NAME"]
        file_path = st.secrets["FILE_PATH"]
        branch = st.secrets.get("branch", "main")
        
        # 2. 连接 GitHub
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 3. 获取当前文件的 SHA (更新文件必须提供)
        contents = repo.get_contents(file_path, ref=branch)
        
        # 4. 转换数据格式
        json_content = json.dumps(new_data, indent=2, ensure_ascii=False)
        
        # 5. 提交更新
        repo.update_file(
            path=contents.path,
            message="[Streamlit] Delete color ramp",
            content=json_content,
            sha=contents.sha,
            branch=branch
        )
        return True, "GitHub Sync Successful"
    except Exception as e:
        return False, str(e)

def delete_permanent(name_to_delete):
    """永久删除：读数据 -> 删条目 -> 同步 GitHub -> 更新本地缓存"""
    
    # 1. 获取当前数据 (优先从内存/本地读，因为 GitHub API 有延迟且有速率限制)
    all_data, _ = load_data_raw()
    
    # 2. 过滤掉要删除的
    new_data = [r for r in all_data if r['name'] != name_to_delete]
    
    # 3. 尝试同步到 GitHub (如果在 Secrets 里配置了)
    if "GITHUB_TOKEN" in st.secrets:
        with st.spinner('Syncing to GitHub...'):
            success, msg = update_github_file(new_data)
            if not success:
                st.error(f"GitHub Sync Failed: {msg}")
                return # 停止，防止本地和远程不一致
            else:
                st.toast(f"Deleted '{name_to_delete}' from GitHub!", icon="🗑️")
    else:
        # 如果没配置 GitHub，仅本地删除 (本地调试用)
        st.warning("No GitHub secrets found. Deleting locally only.")
    
    # 4. 更新本地文件 (为了让页面立刻显示变化)
    try:
        with open('palettes.json', 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
    except:
        pass

    # 5. 清理 Session
    if name_to_delete in st.session_state.selected_ramps:
        st.session_state.selected_ramps.remove(name_to_delete)
    
    # on_click 结束后会自动 rerun

def load_data_raw():
    """读取 JSON 数据"""
    file_path = 'palettes.json'
    # 在生产环境中，为了保证数据最新，这里其实应该从 GitHub 拉取
    # 但为了速度，通常还是读本地，依靠 Streamlit 重启或手动部署来拉取最新
    # 如果 delete_permanent 成功写入了本地，读本地也是 OK 的
    if not os.path.exists(file_path):
        return [], None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                flat = []
                for sub in data: flat.extend(sub)
                data = flat
            return data, None
    except Exception as e:
        return [], str(e)

# --- 颜色工具 ---
def hex_to_rgb(hex_code):
    try: h = hex_code.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return (0,0,0)

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
all_ramps, error_msg = load_data_raw()

if error_msg:
    st.error(f"❌ 数据文件损坏: {error_msg}")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown("###  Library")
    cats = sorted(list(set(r.get('category', '其他') for r in all_ramps)))
    if "韦斯·安德森" in cats: cats.remove("韦斯·安德森"); cats.insert(0, "韦斯·安德森")
    selected_cat = st.selectbox("Category", ["All"] + cats)
    search_query = st.text_input("Search", placeholder="Movies, colors...")
    st.divider()
    count = len(st.session_state.selected_ramps)
    st.markdown(f"**Export List ({count})**")
    if count > 0:
        export_data = [r for r in all_ramps if r['name'] in st.session_state.selected_ramps]
        st.download_button("Download JSON Bundle", json.dumps(export_data, indent=2, ensure_ascii=False), "gis_color_bundle.json", "application/json", type="primary", use_container_width=True)
        if st.button("Clear Selection", use_container_width=True): st.session_state.selected_ramps = []; st.rerun()
    else: st.caption("Select palettes to create a bundle.")

# --- Main ---
st.markdown("""<div class="hero-container"><div class="hero-title">Color Library.</div><div class="hero-subtitle">Curated palettes for cinematic maps.</div></div>""", unsafe_allow_html=True)

filtered_ramps = all_ramps
if selected_cat != "All": filtered_ramps = [r for r in filtered_ramps if r.get('category', '其他') == selected_cat]
if search_query: q = search_query.lower(); filtered_ramps = [r for r in filtered_ramps if q in r['name'].lower()]

if not filtered_ramps:
    st.warning("No palettes found matching your criteria.")
else:
    cols = st.columns(4)
    for idx, ramp in enumerate(filtered_ramps):
        with cols[idx % 4]:
            st.markdown(f"""<div class="apple-card"><div class="gradient-bar" style="background: {get_gradient_css(ramp['colors'])}"></div><div class="card-title" title="{ramp['name']}">{ramp['name']}</div></div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            name = ramp['name']
            with c1:
                is_selected = name in st.session_state.selected_ramps
                btn_label = "✓ Added" if is_selected else "＋ Add"
                if st.button(btn_label, key=f"sel_{idx}", on_click=toggle_select, args=(name,), type="secondary" if is_selected else "secondary", use_container_width=True): pass 
            with c2:
                st.download_button("⬇ CLR", generate_clr(ramp['colors']), f"{name}.clr", key=f"dl_{idx}", use_container_width=True)
            if st.button("Trash", key=f"del_{idx}", on_click=delete_permanent, args=(name,), type="primary", use_container_width=True): pass
            st.markdown("<div style='margin-bottom: 24px'></div>", unsafe_allow_html=True)
