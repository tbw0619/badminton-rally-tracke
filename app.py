import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import Counter

# ===== ページ設定 & 余白圧縮 =====
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

st.markdown(
    """
    <style>
    .block-container{padding-top:0.35rem;padding-bottom:0.35rem;max-width:1500px}
    [data-testid="stHeader"]{height:2rem}
    /* ボタン極小化 */
    div.stButton>button { padding:2px 4px; font-size:11px; line-height:1.1; height:24px; min-height:24px; }
    /* カラム上下の余白を圧縮 */
    [data-testid="column"]{padding-top:0rem;padding-bottom:0rem}
    /* セクション見出しの上下余白を抑制 */
    h3, h4 { margin-top:0.4rem; margin-bottom:0.4rem; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🏸 Badminton Rally Tracker — Web版")

# ====== セッション状態 ======
if "rallies" not in st.session_state:
    st.session_state.rallies = []
if "current_rally" not in st.session_state:
    st.session_state.current_rally = []
if "scores" not in st.session_state:
    st.session_state.scores = {"home": 0, "visitor": 0}

rallies = st.session_state.rallies
current_rally = st.session_state.current_rally
scores = st.session_state.scores

# ====== コート描画関数（軌跡・統計・ボタン背景共通） ======
def draw_court(ax, face="green"):
    ax.set_facecolor(face)
    # 外枠: 幅1, 高さ2 の縦長
    court = patches.Rectangle((0, 0), 1, 2, linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(court)
    # センターライン
    ax.axhline(1, color="white", linewidth=2)
    # インナー矩形（例：サービスエリアのイメージ）
    inner = patches.Rectangle((0.1, 0.3), 0.8, 1.4, linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(inner)
    ax.set_xlim(0, 1); ax.set_ylim(0, 2); ax.axis("off")

def fig_court(width_in=2.6, height_in=4.2, face="green"):
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    draw_court(ax, face=face)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return fig, ax

# 軌跡
def plot_rally(ax, rally):
    draw_court(ax)
    for i, (x, y) in enumerate(rally):
        ax.plot(x, y, "o", ms=4, color="#FFD700")  # 点
        ax.text(x, y, str(i+1), color="white", fontsize=8, ha="center", va="center")
        if i > 0:
            x0, y0 = rally[i-1]
            ax.arrow(x0, y0, x-x0, y-y0, head_width=0.02, head_length=0.03, color="#1f77b4", length_includes_head=True)

# 統計（5×10のヒート的分布）
def plot_stats(ax, rallies):
    draw_court(ax)
    if not rallies:
        return
    all_points = [pt for rally in rallies for pt in rally]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    h = ax.hist2d(xs, ys, bins=[5, 10], range=[[0, 1], [0, 2]], cmap="Reds", alpha=0.6)
    # ％表示（各セルの中央に）
    import numpy as np
    counts = h[0]
    total = counts.sum() if counts.sum() > 0 else 1
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            if counts[i, j] > 0:
                cx = (i + 0.5) / counts.shape[0]
                cy = (j + 0.5) / counts.shape[1] * 2  # yは0..2
                ax.text(cx, cy, f"{counts[i,j]/total*100:0.1f}%", color="white", fontsize=7, ha="center", va="center")

# ====== レイアウト確保（プレースホルダ） ======
col1, col2, col3 = st.columns([1, 1, 1], gap="small")
plot_traj_ph = col1.empty()
plot_stats_ph = col2.empty()

# ====== 右カラム：先にボタンクリックを処理（→即時反映） ======
with col3:
    st.subheader("ボタン", divider="gray")

    # 背景コート（ホーム）：少し明るいグリーン
    fig_bg_home, _ = fig_court(width_in=2.6, height_in=2.0, face="#228B22")
    st.pyplot(fig_bg_home, use_container_width=False)

    # ホーム 5x5 ボタン
    rows, cols = 5, 5
    st.markdown("**ホーム**")
    clicked = None
    for r in range(rows):
        row_cols = st.columns(cols, gap="small")
        for c in range(cols):
            if row_cols[c].button(f"H{r+1},{c+1}", key=f"h-{r}-{c}"):
                clicked = (c, r, "home")

    # 背景コート（ビジター）：少し濃いグリーン
    fig_bg_vis, _ = fig_court(width_in=2.6, height_in=2.0, face="#1E6E1E")
    st.pyplot(fig_bg_vis, use_container_width=False)

    # ビジター 5x5 ボタン
    st.markdown("**ビジター**")
    for r in range(rows):
        row_cols = st.columns(cols, gap="small")
        for c in range(cols):
            if row_cols[c].button(f"V{r+1},{c+1}", key=f"v-{r}-{c}"):
                clicked = (c, r, "visitor")

    # クリックを処理（先に状態を更新）
    if clicked is not None:
        c, r, side = clicked
        # セル中心 => x: (c+0.5)/5,  y: 上が2.0 〜 下が0.0（上を2基準にして可視化）
        x = (c + 0.5) / cols
        # ホーム面は y: 1.0〜2.0、ビジター面は y: 0.0〜1.0 にマッピング
        if side == "home":
            y = 2.0 - (r + 0.5) / rows   # 上から下
        else:
            y = 1.0 - (r + 0.5) / rows   # 上から下（下半分）
        current_rally.append((x, y))
        st.session_state.current_rally = current_rally  # 保存

    # 操作ボタン群
    st.divider()
    c1, c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):
        if current_rally:
            rallies.append(current_rally[:])
            st.session_state.rallies = rallies
            st.session_state.current_rally = []
            # スコアは簡易にホーム加点：必要に応じてロジック差し替え
            scores["home"] += 1
            st.session_state.scores = scores
    if c2.button("元に戻す", use_container_width=True):
        if current_rally:
            current_rally.pop()
            st.session_state.current_rally = current_rally

    c3, c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True):
        if rallies:
            st.session_state.current_rally = rallies.pop()
            st.session_state.rallies = rallies
    if c4.button("ラリー全消去", use_container_width=True):
        st.session_state.rallies = []
        st.session_state.current_rally = []
        st.session_state.scores = {"home": 0, "visitor": 0}

# ====== 左・中央：最新状態で描画（遅延なし） ======
with col1:
    st.subheader("軌跡", divider="gray")
    if current_rally:
        fig, ax = fig_court(width_in=2.6, height_in=4.6)
        plot_rally(ax, current_rally)
    else:
        fig, ax = fig_court(width_in=2.6, height_in=4.6)
    plot_traj_ph.pyplot(fig, use_container_width=False)

with col2:
    st.subheader("統計", divider="gray")
    fig2, ax2 = fig_court(width_in=2.6, height_in=4.6)
    plot_stats(ax2, rallies)
    plot_stats_ph.pyplot(fig2, use_container_width=False)

# ====== スコア表示 ======
st.markdown(f"**スコア:** ホーム {scores['home']} - ビジター {scores['visitor']}")
