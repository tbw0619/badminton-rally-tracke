import io
import math
from collections import Counter

from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ---- page_config は環境で例外化することがあるのでガード ----
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

# 余白を詰めて3カラムが1画面に収まるようにする
st.markdown("""
<style>
/* 上下余白と本文幅を詰める */
.block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; max-width: 1400px; }
[data-testid="stHeader"] { height: 2rem; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 定数（ベース座標）
# -----------------------------
GRID_ROWS = 4
GRID_COLS = 5
BTN_W = 75
BTN_H = 70
MARGIN_X = 15
MARGIN_Y_HOME = 15
MARGIN_Y_VIS = 350
SCALE = 1.1
BASE_W = int(400 * SCALE)   # 描画はこの固定サイズで行い、表示時に縮小
BASE_H = int(680 * SCALE)
LINE_Y_MID = int(329 * SCALE)

HOME_STR = "ホーム"
VIS_STR = "ビジター"

GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
YELLOW = (255, 215, 0)

# -----------------------------
# セッション初期化
# -----------------------------
if "init" not in st.session_state:
    S = st.session_state
    S.init = True
    S.game_number = 1
    S.home_score = 0
    S.vis_score = 0
    S.path_data = []          # [(x,y,coat,label)]  x,y はBASE_W/BASE_H基準
    S.click_count = 0
    S.all_paths = []
    S.final_positions = []
    S.rally_count = 1
    S.game_scores = []
    S.home = HOME_STR
    S.visitor = VIS_STR
    S.home_color = RED
    S.vis_color = BLUE
    S.rally_states = []
    S.game_states = []
S = st.session_state

# -----------------------------
# グリッド・ラベル
# -----------------------------
HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}

def button_text(coat: str, i: int, j: int) -> str:
    if coat == S.home:
        return f"out{coat}\n({i},{j})" if (i, j) in HOME_OUTS else f"{coat}\n({i},{j})"
    else:
        return f"out{coat}\n({i},{j})" if (i, j) in VIS_OUTS else f"{coat}\n({i},{j})"

def center_xy(col_idx: int, row_idx: int, coat: str) -> tuple[int,int]:
    j = col_idx - 1
    i = row_idx - 1
    x = int((MARGIN_X * SCALE) + j * (76 * SCALE) + BTN_W/2)
    y0 = int((MARGIN_Y_HOME if coat == S.home else MARGIN_Y_VIS) * SCALE)
    y = int(y0 + i * (76 * SCALE) + BTN_H/2)
    return x, y

# -----------------------------
# スコア
# -----------------------------
SCORING_BTNS_HOME = {
    f"out{HOME_STR}\n(1,1)", f"out{HOME_STR}\n(1,2)", f"out{HOME_STR}\n(1,3)", f"out{HOME_STR}\n(1,4)", f"out{HOME_STR}\n(1,5)",
    f"out{HOME_STR}\n(2,1)", f"out{HOME_STR}\n(3,1)", f"out{HOME_STR}\n(4,1)", f"out{HOME_STR}\n(2,5)", f"out{HOME_STR}\n(3,5)", f"out{HOME_STR}\n(4,5)",
    f"{VIS_STR}\n(1,2)", f"{VIS_STR}\n(1,3)", f"{VIS_STR}\n(1,4)", f"{VIS_STR}\n(2,2)", f"{VIS_STR}\n(2,3)", f"{VIS_STR}\n(2,4)",
    f"{VIS_STR}\n(3,2)", f"{VIS_STR}\n(3,3)", f"{VIS_STR}\n(3,4)", f"{VIS_STR}\n(4,2)", f"{VIS_STR}\n(4,3)", f"{VIS_STR}\n(4,4)"
}
def update_score(last_button_name: str):
    if S.game_number % 2 == 0:
        S.vis_score += 1 if last_button_name in SCORING_BTNS_HOME else 0
        S.home_score += 0 if last_button_name in SCORING_BTNS_HOME else 1
    else:
        S.home_score += 1 if last_button_name in SCORING_BTNS_HOME else 0
        S.vis_score += 0 if last_button_name in SCORING_BTNS_HOME else 1

# -----------------------------
# 描画
# -----------------------------
try:
    FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT_SMALL = ImageFont.load_default()

def draw_arrow(d: ImageDraw.ImageDraw, x1,y1,x2,y2, color, width=2):
    d.line((x1,y1,x2,y2), fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 8
    a1 = ang + math.radians(160)
    a2 = ang - math.radians(160)
    p1 = (x2 + L*math.cos(a1), y2 + L*math.sin(a1))
    p2 = (x2 + L*math.cos(a2), y2 + L*math.sin(a2))
    d.polygon([p1, (x2, y2), p2], fill=color)

def render_court(paths=None, show_step_numbers=True) -> Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    d = ImageDraw.Draw(img)
    # mid line & inner rect
    d.line((0, LINE_Y_MID, BASE_W, LINE_Y_MID), fill=WHITE, width=2)
    x1 = int((11 + 1 * 76) * SCALE); y1 = int((11 + 1 * 76) * SCALE)
    x2 = int((11 + 4 * 76) * SCALE); y2 = int((346 + 3 * 76) * SCALE)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)
    # path
    if paths:
        for idx in range(len(paths)):
            x,y,coat,label = paths[idx]
            if idx == 0: d.ellipse((x-5, y-5, x+5, y+5), fill=YELLOW)
            if idx > 0:
                px,py,pcoat,_ = paths[idx-1]
                if pcoat == S.home and coat == S.visitor: color = S.home_color
                elif pcoat == S.visitor and coat == S.home: color = S.vis_color
                else: color = S.home_color if coat == S.home else S.vis_color
                draw_arrow(d, px,py,x,y,color)
                if show_step_numbers:
                    mx, my = (px+x)/2, (py+y)/2
                    offset = -10 if coat == "ホーム" else 10
                    d.text((mx, my+offset), str(idx+1), fill=WHITE, font=FONT_SMALL, anchor="mm")
    return img

def render_stats_image() -> Image.Image:
    home_counter = Counter([p for p in S.final_positions if S.home in p])
    vis_counter  = Counter([p for p in S.final_positions if S.visitor in p])
    total_home, total_vis = sum(home_counter.values()), sum(vis_counter.values())
    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    d = ImageDraw.Draw(img)
    d.line((0, LINE_Y_MID, BASE_W, LINE_Y_MID), fill=WHITE, width=2)
    x1 = int((11 + 1 * 76) * SCALE); y1 = int((11 + 1 * 76) * SCALE)
    x2 = int((11 + 4 * 76) * SCALE); y2 = int((346 + 3 * 76) * SCALE)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)
    for i in range(1, GRID_ROWS+1):
        for j in range(1, GRID_COLS+1):
            for coat in (S.home, S.visitor):
                label = button_text(coat, i, j)
                cx, cy = center_xy(j, i, coat)
                if coat == S.home:
                    cnt = home_counter.get(label, 0); pct = (cnt/total_home*100) if total_home else 0
                    color = RED if S.home == "ホーム" else BLUE
                else:
                    cnt = vis_counter.get(label, 0); pct = (cnt/total_vis*100) if total_vis else 0
                    color = BLUE if S.visitor == "ホーム" else RED
                d.text((cx, cy), f"{pct:.1f}%", fill=color, font=FONT_SMALL, anchor="mm")
    return img

# -----------------------------
# 操作系
# -----------------------------
def add_point(coat: str, i: int, j: int):
    x,y = center_xy(j, i, coat)      # ベース座標
    S.click_count += 1
    S.path_data.append((x, y, coat, button_text(coat, i, j)))

def end_rally():
    if S.path_data:
        last_lbl = S.path_data[-1][3]
        S.final_positions.append(last_lbl)
        update_score(last_lbl)
        S.all_paths.append(list(S.path_data))
    S.path_data = []
    S.click_count = 0
    S.rally_count += 1
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
    S.path_data = []; S.click_count = 0

def switch_game():
    S.game_scores.append((S.game_number, S.home_score, S.vis_score))
    S.final_positions = []; S.home_score = 0; S.vis_score = 0
    S.rally_count = 1; S.path_data = []; S.click_count = 0; S.all_paths = []
    S.game_number += 1
    S.home_color, S.vis_color = (BLUE, RED) if S.game_number % 2 == 0 else (RED, BLUE)
    S.home, S.visitor = S.visitor, S.home

# -----------------------------
# レイアウト（3カラム固定）
# -----------------------------
# 1画面に収めるための表示幅・高さ。必要ならサイドバーで微調整可。
st.sidebar.header("表示サイズ調整（必要時のみ）")
col_w = st.sidebar.slider("各カラムの横幅(px)", 260, 520, 360, 10)
img_h  = st.sidebar.slider("コート画像の高さ(px)", 360, 720, 520, 10)

col1, col2, col3 = st.columns(3, gap="small")

# ヘッダ
st.markdown(
    f"**ゲーム {S.game_number}**　—　スコア：**{S.home} {S.home_score} - {S.visitor} {S.vis_score}**"
)

# ① 軌跡コート
with col1:
    st.subheader("軌跡コート", divider="gray")
    img = render_court(S.path_data, True)
    # 高さに合わせてリサイズ（アスペクト維持）
    disp = img.resize((int(BASE_W * (img_h/BASE_H)), int(img_h)), Image.NEAREST)
    st.image(disp, use_column_width=False)

# ② 統計コート
with col2:
    st.subheader("統計表示コート", divider="gray")
    stats_img = render_stats_image()
    disp2 = stats_img.resize((int(BASE_W * (img_h/BASE_H)), int(img_h)), Image.NEAREST)
    st.image(disp2, use_column_width=False)
    # ミスランキング（簡潔表示）
    if S.final_positions:
        cnt = Counter(S.final_positions)
        ranked = sorted(cnt.items(), key=lambda x: x[1], reverse=True)[:8]
        st.caption("ミスランキング（最終着弾の多い順）")
        for idx, (pos, c) in enumerate(ranked, start=1):
            pos_clean = pos.replace("\n", " ")
            st.write(f"{idx}. {pos_clean} — {c} 回")
    else:
        st.info("データ未集計（ラリー終了で反映）")

# ③ ボタンコート（ホーム・ビジターを上下にコンパクト配置）
with col3:
    st.subheader("ボタンコート", divider="gray")
    st.markdown(f"**{S.home}**")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.home, i, j)
            if cols[j-1].button(label, key=f"h-{S.game_number}-{S.rally_count}-{i}-{j}"):
                add_point(S.home, i, j)

    st.markdown(f"**{S.visitor}**")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.visitor, i, j)
            if cols[j-1].button(label, key=f"v-{S.game_number}-{S.rally_count}-{i}-{j}"):
                add_point(S.visitor, i, j)

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("ラリー終了", use_container_width=True): end_rally()
    if c2.button("元に戻す", use_container_width=True): undo_last_path()

    c3, c4 = st.columns(2)
    if c3.button("一つ前のラリーに戻る", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True): reset_current_rally()

    st.divider()
    if st.button("ゲーム切り替え", use_container_width=True): switch_game()
