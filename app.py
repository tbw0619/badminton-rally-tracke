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

with col3:
    st.subheader("ボタンコート")
    # 背景にコート描画
    fig, ax = plt.subplots(figsize=(2.6, 4.8))
    draw_court(ax)
    st.pyplot(fig, clear_figure=True)

    rows, cols = 5, 5
    for r in range(rows):
        cols_layout = st.columns(cols)
        for c in range(cols):
            if cols_layout[c].button(f"{r+1},{c+1}", key=f"btn-{r}-{c}"):
                pt = ((c+0.5)/cols, 2-(r+0.5)/rows)
                current_rally.append(pt)
                st.session_state["current_rally"] = current_rally
                # 即時反映のため rerun は不要

# 操作用ボタン
actions = st.columns(3)
if actions[0].button("ラリー終了"):
    if current_rally:
        rallies.append(current_rally)
        st.session_state["rallies"] = rallies
        st.session_state["current_rally"] = []
        scores["home"] += 1
        st.session_state["scores"] = scores

if actions[1].button("元に戻す"):
    if current_rally:
        current_rally.pop()
        st.session_state["current_rally"] = current_rally

if actions[2].button("全消去"):
    st.session_state["rallies"] = []
    st.session_state["current_rally"] = []
    st.session_state["scores"] = {"home": 0, "visitor": 0}

# スコア表示
st.markdown(f"### スコア: ホーム {scores['home']} - ビジター {scores['visitor']}")

# CSS調整（ボタン小型化 + レイテンシ削減）
st.markdown(
    """
    <style>
    div.stButton>button {
        height: 26px;
        font-size: 11px;
        padding: 0;
        margin: 1px;
    }
    </style>
    """,
    unsafe_allow_html=True
)
