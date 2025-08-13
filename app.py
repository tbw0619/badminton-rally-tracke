import io
import math
from collections import Counter

from PIL import Image, ImageDraw, ImageFont
import streamlit as st

"""
🏸 Badminton Rally Tracker — Web版 (Streamlit)

■ これは元の Tkinter アプリを Web で誰でも使えるようにした移植版です。
  - ボタンをクリックしてラリーの着弾点を記録
  - コート画像に軌跡（矢印）と手順番号を描画
  - スコア自動計算（元コードのロジックを踏襲）
  - 統計（最終着弾の割合）とミスランキング表示
  - PNG のダウンロード（自動保存はブラウザでは不可）

■ デプロイは Streamlit Community Cloud / Hugging Face Spaces で可能です。
  - requirements.txt に `streamlit` と `pillow` を指定してください。

※ OS依存の pyautogui / pygetwindow / ImageGrab はクラウドでは動かないため削除しています。
"""

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
st.title("🏸 Badminton Rally Tracker — Web版 (Streamlit)")
st.caption("Tkinter版をWeb対応に移植。クリックでラリーを記録し、スコア・軌跡・統計を保存できます。")

# -----------------------------
# Constants
# -----------------------------
GRID_ROWS = 4
GRID_COLS = 5
BTN_W = 75
BTN_H = 70
MARGIN_X = 15
MARGIN_Y_HOME = 15
MARGIN_Y_VIS = 350
SCALE = 1.1
CANVAS_W = int(400 * SCALE)
CANVAS_H = int(680 * SCALE)
LINE_Y_MID = int(329 * SCALE)

HOME_STR = "ホーム"
VIS_STR = "ビジター"

# Colors in PIL (RGB)
GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
YELLOW = (255, 215, 0)

# -----------------------------
# Session State Initialization
# -----------------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.game_number = 1
    st.session_state.home_score = 0
    st.session_state.vis_score = 0
    st.session_state.path_data = []      # [(x, y, coat, button_text)]
    st.session_state.click_count = 0
    st.session_state.all_paths = []      # list of rallies (list of path points)
    st.session_state.final_positions = []  # list of button_text at rally end
    st.session_state.rally_count = 1
    st.session_state.game_scores = []
    st.session_state.home = HOME_STR
    st.session_state.visitor = VIS_STR
    st.session_state.home_color = RED
    st.session_state.vis_color = BLUE
    st.session_state.rally_states = []   # undo for rally
    st.session_state.game_states = []    # history snapshots

S = st.session_state  # alias

# -----------------------------
# Utility: Grid geometry & labels
# -----------------------------
def grid_xy(col_idx: int, row_idx: int, coat: str):
    """Return pixel center (x, y) for given grid cell (1-based) and coat."""
    j = col_idx - 1
    i = row_idx - 1
    x = (MARGIN_X * SCALE) + j * (76 * SCALE) + BTN_W/2
    y0 = (MARGIN_Y_HOME if coat == S.home else MARGIN_Y_VIS) * SCALE
    y = y0 + i * (76 * SCALE) + BTN_H/2
    return int(x), int(y)

HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}

def button_text(coat: str, i: int, j: int):
    if coat == S.home:
        label = f"out{coat}\n({i},{j})" if (i, j) in HOME_OUTS else f"{coat}\n({i},{j})"
    else:
        label = f"out{coat}\n({i},{j})" if (i, j) in VIS_OUTS else f"{coat}\n({i},{j})"
    return label

# -----------------------------
# Scoring Logic (from original)
# -----------------------------
SCORING_BTNS_HOME = {
    f"out{HOME_STR}\n(1,1)", f"out{HOME_STR}\n(1,2)", f"out{HOME_STR}\n(1,3)", f"out{HOME_STR}\n(1,4)", f"out{HOME_STR}\n(1,5)",
    f"out{HOME_STR}\n(2,1)", f"out{HOME_STR}\n(3,1)", f"out{HOME_STR}\n(4,1)", f"out{HOME_STR}\n(2,5)", f"out{HOME_STR}\n(3,5)", f"out{HOME_STR}\n(4,5)",
    f"{VIS_STR}\n(1,2)", f"{VIS_STR}\n(1,3)", f"{VIS_STR}\n(1,4)", f"{VIS_STR}\n(2,2)", f"{VIS_STR}\n(2,3)", f"{VIS_STR}\n(2,4)",
    f"{VIS_STR}\n(3,2)", f"{VIS_STR}\n(3,3)", f"{VIS_STR}\n(3,4)", f"{VIS_STR}\n(4,2)", f"{VIS_STR}\n(4,3)", f"{VIS_STR}\n(4,4)"
}

def update_score(last_button_name: str):
    if S.game_number % 2 == 0:
        # even game: reversed
        if last_button_name in SCORING_BTNS_HOME:
            S.vis_score += 1
        else:
            S.home_score += 1
    else:
        if last_button_name in SCORING_BTNS_HOME:
            S.home_score += 1
        else:
            S.vis_score += 1

# -----------------------------
# Rendering: court & paths (PIL)
# -----------------------------
try:
    FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT_SMALL = ImageFont.load_default()

def draw_arrow(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color, width=2):
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 8
    a1 = ang + math.radians(160)
    a2 = ang - math.radians(160)
    p1 = (x2 + L * math.cos(a1), y2 + L * math.sin(a1))
    p2 = (x2 + L * math.cos(a2), y2 + L * math.sin(a2))
    draw.polygon([p1, (x2, y2), p2], fill=color)

def render_court(paths=None, show_step_numbers=True):
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), GREEN)
    d = ImageDraw.Draw(img)

    # mid line
    d.line((0, LINE_Y_MID, CANVAS_W, LINE_Y_MID), fill=WHITE, width=2)

    # inner rect
    x1 = int((11 + 1 * 76) * SCALE)
    y1 = int((11 + 1 * 76) * SCALE)
    x2 = int((11 + 4 * 76) * SCALE)
    y2 = int((346 + 3 * 76) * SCALE)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)

    # path points from current rally
    if paths:
        for idx in range(len(paths)):
            x, y, coat, btn_text = paths[idx]
            # first point
            if idx == 0:
                d.ellipse((x-5, y-5, x+5, y+5), fill=YELLOW)
            if idx > 0:
                px, py, coat_prev, _ = paths[idx-1]
                # colors depending on coat change
                if coat_prev == S.home and coat == S.visitor:
                    color = S.home_color
                elif coat_prev == S.visitor and coat == S.home:
                    color = S.vis_color
                else:
                    color = S.home_color if coat == S.home else S.vis_color
                draw_arrow(d, px, py, x, y, color)
                # step numbers
                if show_step_numbers:
                    mx = (px + x) / 2
                    my = (py + y) / 2
                    offset = -10 if coat == HOME_STR else 10
                    d.text((mx, my + offset), str(idx+1), fill=WHITE, font=FONT_SMALL, anchor="mm")
    return img

# -----------------------------
# Actions (state mutations)
# -----------------------------
def click_cell(coat: str, i: int, j: int):
    x, y = grid_xy(j, i, coat)
    S.click_count += 1
    S.path_data.append((x, y, coat, button_text(coat, i, j)))

def end_rally():
    if S.path_data:
        last_btn = S.path_data[-1][3]
        S.final_positions.append(last_btn)
        update_score(last_btn)
        S.all_paths.append(list(S.path_data))
    S.path_data = []
    S.click_count = 0
    S.rally_count += 1
    # snapshot for undo
    S.game_states.append((S.home_score, S.vis_score, S.rally_count, list(S.path_data),
                          S.click_count, list(S.all_paths), list(S.final_positions)))
    S.rally_states.append((S.home_score, S.vis_score, S.rally_count, list(S.path_data),
                           S.click_count, list(S.all_paths), list(S.final_positions)))

def undo_last_path():
    if S.path_data:
        S.path_data.pop()
        S.click_count = max(0, S.click_count - 1)

def undo_last_rally():
    if S.rally_states:
        (S.home_score, S.vis_score, S.rally_count, S.path_data,
         S.click_count, S.all_paths, S.final_positions) = S.rally_states.pop()

def reset_current_rally():
    S.path_data = []
    S.click_count = 0

def switch_game():
    # record previous game's final score
    S.game_scores.append((S.game_number, S.home_score, S.vis_score))
    # reset
    S.final_positions = []
    S.home_score = 0
    S.vis_score = 0
    S.rally_count = 1
    S.path_data = []
    S.click_count = 0
    S.all_paths = []
    # next game
    S.game_number += 1
    # color swap by parity (original behavior)
    if S.game_number % 2 == 0:
        S.home_color, S.vis_color = BLUE, RED
    else:
        S.home_color, S.vis_color = RED, BLUE
    # swap side labels
    S.home, S.visitor = S.visitor, S.home

# -----------------------------
# Stats & Ranking images
# -----------------------------
def render_stats_image():
    # gather counts for home/visitor areas separately
    home_counter = Counter([p for p in S.final_positions if S.home in p])
    vis_counter  = Counter([p for p in S.final_positions if S.visitor in p])
    total_home = sum(home_counter.values())
    total_vis = sum(vis_counter.values())

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), GREEN)
    d = ImageDraw.Draw(img)
    # court
    d.line((0, LINE_Y_MID, CANVAS_W, LINE_Y_MID), fill=WHITE, width=2)
    x1 = int((11 + 1 * 76) * SCALE)
    y1 = int((11 + 1 * 76) * SCALE)
    x2 = int((11 + 4 * 76) * SCALE)
    y2 = int((346 + 3 * 76) * SCALE)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)

    def center_of(coat: str, i: int, j: int):
        return grid_xy(j, i, coat)

    # draw percentages
    for i in range(1, GRID_ROWS + 1):
        for j in range(1, GRID_COLS + 1):
            for coat in (S.home, S.visitor):
                label = button_text(coat, i, j)
                cx, cy = center_of(coat, i, j)
                if coat == S.home:
                    cnt = home_counter.get(label, 0)
                    pct = (cnt / total_home * 100) if total_home else 0
                    color = RED if S.home == "ホーム" else BLUE
                else:
                    cnt = vis_counter.get(label, 0)
                    pct = (cnt / total_vis * 100) if total_vis else 0
                    color = BLUE if S.visitor == "ホーム" else RED
                d.text((cx, cy), f"{pct:.1f}%", fill=color, font=FONT_SMALL, anchor="mm")
    return img

# -----------------------------
# UI Layout
# -----------------------------
left, right = st.columns([1.2, 1])

with left:
    st.subheader("記録パネル")
    # Score header
    st.markdown(f"**ゲーム {S.game_number}**  —  スコア：**{S.home} {S.home_score} - {S.visitor} {S.vis_score}**")

    # Current court render
    court_img = render_court(S.path_data, show_step_numbers=True)
    buf = io.BytesIO()
    court_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    st.image(png_bytes, caption="現在のラリー軌跡", use_column_width=False)
    st.download_button(
        "この画像をPNGでダウンロード",
        data=png_bytes,
        file_name=f"game{S.game_number}_rally{S.rally_count}_preview.png",
        mime="image/png"
    )

    st.divider()
    st.markdown(f"### {S.home} のコート")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.home, i, j)
            if cols[j-1].button(label, key=f"home-{S.game_number}-{S.rally_count}-{i}-{j}"):
                click_cell(S.home, i, j)

    st.markdown(f"### {S.visitor} のコート")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.visitor, i, j)
            if cols[j-1].button(label, key=f"vis-{S.game_number}-{S.rally_count}-{i}-{j}"):
                click_cell(S.visitor, i, j)

with right:
    st.subheader("操作")
    c1, c2 = st.columns(2)
    if c1.button("ラリー終了", use_container_width=True):
        end_rally()
        try:
            st.toast("ラリーを確定しました。スコアと履歴に反映。")
        except Exception:
            pass
    if c2.button("現在の入力を取り消す", use_container_width=True):
        undo_last_path()

    c3, c4 = st.columns(2)
    if c3.button("一つ前のラリーに戻る", use_container_width=True):
        undo_last_rally()
    if c4.button("ラリー全消去（リセット）", use_container_width=True):
        reset_current_rally()

    st.divider()
    if st.button("ゲーム切り替え", use_container_width=True):
        prev = (S.game_number, S.home_score, S.vis_score)
        switch_game()
        try:
            st.toast(f"ゲーム {prev[0]} の結果: {S.home} {prev[1]} - {S.visitor} {prev[2]}。サイド・色を切り替えました。")
        except Exception:
            pass

    st.divider()
    st.markdown("### 統計 & ランキング")
    stats_img = render_stats_image()
    sbuf = io.BytesIO()
    stats_img.save(sbuf, format="PNG")
    stats_png = sbuf.getvalue()
    st.image(stats_png, caption="最終着弾の割合（ホーム/ビジター別）")
    st.download_button(
        "統計画像をPNGでダウンロード",
        data=stats_png,
        file_name=f"game{S.game_number}_stats.png",
        mime="image/png"
    )

    # Mistake ranking (most common final positions)
    if S.final_positions:
        cnt = Counter(S.final_positions)
        ranked = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
        st.markdown("#### ミスランキング（最終着弾の多い順）")
        for rank, (pos, c) in enumerate(ranked, start=1):
            st.write(f"{rank}. {pos.replace('\\n',' ')} — {c} 回")
    else:
        st.info("まだ最終着弾データがありません。ラリーをいくつか確定すると表示されます。")

st.divider()
st.markdown(
    """
**使い方メモ**  
1) コート上のボタンをクリックすると、そのマスの中心に点が打たれ、以降は矢印で軌跡が描かれます。  
2) ラリー終了 → 最後に押したボタンを最終着弾としてスコア計算し、ラリー履歴に追加します。  
3) 統計は「最終着弾」だけを集計してホーム/ビジターそれぞれのエリア割合を表示します。  
4) PNG保存は各画像下の「ダウンロード」ボタンから行ってください（自動保存はブラウザ仕様上不可）。  
5) ゲーム切替でスコアをリセットし、サイド名の入替とライン色（赤/青）を自動で入れ替えます。  
"""
)
