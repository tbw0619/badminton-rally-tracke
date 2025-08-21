import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import Counter

# ページ設定
st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")

st.title("🏸 Badminton Rally Tracker — Web版")

# ラリー履歴
rallies = st.session_state.get("rallies", [])
current_rally = st.session_state.get("current_rally", [])
scores = st.session_state.get("scores", {"home": 0, "visitor": 0})

# コート描画関数
def draw_court(ax):
    ax.set_facecolor("green")
    court = patches.Rectangle((0, 0), 1, 2, linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(court)
    ax.axhline(1, color="white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 2)
    ax.axis("off")

# 軌跡表示
def plot_rally(ax, rally):
    draw_court(ax)
    for i, (x, y) in enumerate(rally):
        ax.plot(x, y, "ro")
        ax.text(x, y, str(i+1), color="cyan", fontsize=8, ha="center")
        if i > 0:
            x0, y0 = rally[i-1]
            ax.arrow(x0, y0, x-x0, y-y0, head_width=0.02, head_length=0.02, color="blue")

# 統計表示
def plot_stats(ax, rallies):
    draw_court(ax)
    if not rallies:
        return
    all_points = [pt for rally in rallies for pt in rally]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    ax.hist2d(xs, ys, bins=[5, 10], range=[[0, 1], [0, 2]], cmap="Reds", alpha=0.6)

# UIレイアウト
col1, col2, col3 = st.columns([1,1,1])

with col1:
    st.subheader("軌跡")
    fig, ax = plt.subplots(figsize=(2.6, 4.8))
    if current_rally:
        plot_rally(ax, current_rally)
    st.pyplot(fig, clear_figure=True)

with col2:
    st.subheader("統計")
    fig, ax = plt.subplots(figsize=(2.6, 4.8))
    plot_stats(ax, rallies)
    st.pyplot(fig, clear_figure=True)

# ボタングリッド描画関数
def render_button_grid(title: str, coat: str, key_prefix: str):
    st.markdown(f"#### {title}")
    rows, cols = 4, 5
    for r in range(rows):
        grid = st.columns([9, 1, 9, 9, 9, 1, 9], gap="small")
        # ボタン1
        if grid[0].button(f"{coat[0].upper()}{r+1},1", key=f"{key_prefix}-{r+1}-1"):
            pt = ((0+0.5)/cols, (2-(r+0.5)/(rows*2)) if coat=="home" else (r+0.5)/(rows*2))
            current_rally.append(pt)
            st.session_state["current_rally"] = current_rally
            st.rerun()

        # 縦線（左）
        with grid[1]:
            st.markdown('<div class="grid-vline"></div>', unsafe_allow_html=True)

        # ボタン2〜4
        for idx, c in enumerate([2,3,4], start=2):
            if grid[idx].button(f"{coat[0].upper()}{r+1},{c}", key=f"{key_prefix}-{r+1}-{c}"):
                pt = ((c-0.5)/cols, (2-(r+0.5)/(rows*2)) if coat=="home" else (r+0.5)/(rows*2))
                current_rally.append(pt)
                st.session_state["current_rally"] = current_rally
                st.rerun()

        # 縦線（右）
        with grid[5]:
            st.markdown('<div class="grid-vline"></div>', unsafe_allow_html=True)

        # ボタン5
        if grid[6].button(f"{coat[0].upper()}{r+1},5", key=f"{key_prefix}-{r+1}-5"):
            pt = ((5-0.5)/cols, (2-(r+0.5)/(rows*2)) if coat=="home" else (r+0.5)/(rows*2))
            current_rally.append(pt)
            st.session_state["current_rally"] = current_rally
            st.rerun()

        # 横線
        if r == 0 or r == 3:
            st.markdown('<div class="grid-hline"></div>', unsafe_allow_html=True)

with col3:
    st.subheader("ボタン")
    render_button_grid("ホーム", "home", "H")
    render_button_grid("ビジター", "visitor", "V")

# 操作用ボタン
actions = st.columns(5)
if actions[0].button("ラリー終了"):
    if current_rally:
        rallies.append(current_rally)
        st.session_state["rallies"] = rallies
        st.session_state["current_rally"] = []
        scores["home"] += 1
        st.session_state["scores"] = scores
        st.rerun()

if actions[1].button("元に戻す"):
    if current_rally:
        current_rally.pop()
        st.session_state["current_rally"] = current_rally
        st.rerun()

if actions[2].button("一つ前のラリー"):
    if rallies:
        rallies.pop()
        st.session_state["rallies"] = rallies
        st.rerun()

if actions[3].button("ラリー全消去"):
    st.session_state["rallies"] = []
    st.session_state["current_rally"] = []
    st.session_state["scores"] = {"home": 0, "visitor": 0}
    st.rerun()

if actions[4].button("ゲーム切り替え"):
    st.session_state["rallies"] = []
    st.session_state["current_rally"] = []
    st.session_state["scores"] = {"home": 0, "visitor": 0}
    st.rerun()

# スコア表示
st.markdown(f"### スコア: ホーム {scores['home']} - ビジター {scores['visitor']}")

# CSS調整
st.markdown(
    """
    <style>
    div.stButton>button {
        height: 26px;
        font-size: 11px;
        padding: 0;
        margin: 1px;
        border: 1px solid white !important;
    }
    .grid-vline{width:2px;height:26px;background:#ffffff;border-radius:2px;margin:0 2px;}
    .grid-hline{width:100%;height:2px;background:#ffffff;border-radius:2px;margin:4px 0;}
    </style>
    """,
    unsafe_allow_html=True
)
