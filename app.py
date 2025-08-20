import io
import math
from collections import Counter

from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

# ---- Cloudでpage_config例外が出ても続行できるようにガード ----
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass
# ----------------------------------------------------------------

st.title("🏸 Badminton Rally Tracker — Web版 (Streamlit)")
st.caption("スマホ対応：画像タップ入力でズレなく記録できます。従来のボタン入力も併用可能。")

# =============================
# 定数（基準座標は固定、表示はリサイズ対応）
# =============================
GRID_ROWS = 4
GRID_COLS = 5
BTN_W = 75
BTN_H = 70
MARGIN_X = 15
MARGIN_Y_HOME = 15
MARGIN_Y_VIS = 350
SCALE = 1.1
BASE_W = int(400 * SCALE)   # ベース画像幅（座標計算はこのサイズ基準）
BASE_H = int(680 * SCALE)
LINE_Y_MID = int(329 * SCALE)

HOME_STR = "ホーム"
VIS_STR = "ビジター"

GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
YELLOW = (255, 215, 0)

# =============================
# セッション初期化
# =============================
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

# =============================
# グリッド・ラベル
# =============================
HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}

def button_text(coat: str, i: int, j: int) -> str:
    if coat == S.home:
        return f"out{coat}\n({i},{j})" if (i, j) in HOME_OUTS else f"{coat}\n({i},{j})"
    else:
        return f"out{coat}\n({i},{j})" if (i, j) in VIS_OUTS else f"{coat}\n({i},{j})"

def center_xy(col_idx: int, row_idx: int, coat: str) -> tuple[int,int]:
    """ベース画像座標でセル中心を返す（1始まり）"""
    j = col_idx - 1
    i = row_idx - 1
    x = int((MARGIN_X * SCALE) + j * (76 * SCALE) + BTN_W/2)
    y0 = int((MARGIN_Y_HOME if coat == S.home else MARGIN_Y_VIS) * SCALE)
    y = int(y0 + i * (76 * SCALE) + BTN_H/2)
    return x, y

# =============================
# スコア
# =============================
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

# =============================
# 描画
# =============================
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
    # mid line
    d.line((0, LINE_Y_MID, BASE_W, LINE_Y_MID), fill=WHITE, width=2)
    # inner rect
    x1 = int((11 + 1 * 76) * SCALE)
    y1 = int((11 + 1 * 76) * SCALE)
    x2 = int((11 + 4 * 76) * SCALE)
    y2 = int((346 + 3 * 76) * SCALE)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)
    # path
    if paths:
        for idx in range(len(paths)):
            x,y,coat,label = paths[idx]
            if idx == 0:
                d.ellipse((x-5, y-5, x+5, y+5), fill=YELLOW)
            if idx > 0:
                px,py,pcoat,_ = paths[idx-1]
                if pcoat == S.home and coat == S.visitor:
                    color = S.home_color
                elif pcoat == S.visitor and coat == S.home:
                    color = S.vis_color
                else:
                    color = S.home_color if coat == S.home else S.vis_color
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
                    cnt = home_counter.get(label, 0)
                    pct = (cnt/total_home*100) if total_home else 0
                    color = RED if S.home == "ホーム" else BLUE
                else:
                    cnt = vis_counter.get(label, 0)
                    pct = (cnt/total_vis*100) if total_vis else 0
                    color = BLUE if S.visitor == "ホーム" else RED
                d.text((cx, cy), f"{pct:.1f}%", fill=color, font=FONT_SMALL, anchor="mm")
    return img

# =============================
# 入力: 画像タップ or ボタン
# =============================
st.sidebar.subheader("入力方法")
use_tap = st.sidebar.toggle("画像タップ入力（推奨・スマホ向け）", value=True)
display_width = st.sidebar.slider("表示幅（px）", 300, 900, 440, 10,
                                  help="スマホ画面に合わせて変更。画像の見た目だけを拡大縮小します。")
# 表示サイズに合わせたスケール（ベース座標 → 表示座標）
disp_scale = display_width / BASE_W

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
# UI Layout
# -----------------------------
left, right = st.columns([1.2, 1])

with left:
    st.subheader("記録パネル")
    st.markdown(f"**ゲーム {S.game_number}** — スコア：**{S.home} {S.home_score} - {S.visitor} {S.vis_score}**")

    # 現在のコート画像（ベースで描画→指定幅で表示）
    img = render_court(S.path_data, True)
    disp_img = img.resize((int(BASE_W*disp_scale), int(BASE_H*disp_scale)), Image.NEAREST)

    if use_tap:
        st.caption("画像をタップ／クリックして着弾を記録（スマホ向け）")
        result = streamlit_image_coordinates(disp_img, key=f"tap-{S.game_number}-{S.rally_count}")
        if result is not None:
            # 受け取るのは表示座標 → ベース座標へ逆変換
            rx, ry = result["x"], result["y"]
            bx, by = int(rx / disp_scale), int(ry / disp_scale)
            # どちらのサイドか判定
            coat = S.home if by < LINE_Y_MID else S.visitor
            # 最寄りセル(1..4,1..5)へスナップ
            best_i, best_j, best_d = 1,1,10**9
            for i in range(1, GRID_ROWS+1):
                for j in range(1, GRID_COLS+1):
                    cx, cy = center_xy(j, i, coat)
                    d2 = (cx-bx)**2 + (cy-by)**2
                    if d2 < best_d:
                        best_d, best_i, best_j = d2, i, j
            add_point(coat, best_i, best_j)
            st.rerun()  # 連打時もズレずに更新
    else:
        st.image(disp_img, caption="現在のラリー軌跡", use_column_width=False)

    st.divider()
    st.caption("※ 従来のボタン入力（PC向け）")
    st.markdown(f"### {S.home} のコート")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.home, i, j)
            if cols[j-1].button(label, key=f"h-{S.game_number}-{S.rally_count}-{i}-{j}"):
                add_point(S.home, i, j)

    st.markdown(f"### {S.visitor} のコート")
    for i in range(1, GRID_ROWS + 1):
        cols = st.columns(GRID_COLS)
        for j in range(1, GRID_COLS + 1):
            label = button_text(S.visitor, i, j)
            if cols[j-1].button(label, key=f"v-{S.game_number}-{S.rally_count}-{i}-{j}"):
                add_point(S.visitor, i, j)

with right:
    st.subheader("操作")
    c1, c2 = st.columns(2)
    if c1.button("ラリー終了", use_container_width=True): end_rally()
    if c2.button("現在の入力を取り消す", use_container_width=True): undo_last_path()

    c3, c4 = st.columns(2)
    if c3.button("一つ前のラリーに戻る", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去（リセット）", use_container_width=True): reset_current_rally()

    st.divider()
    if st.button("ゲーム切り替え", use_container_width=True): switch_game()

    st.divider()
    st.markdown("### 統計 & ランキング")
    stats_img = render_stats_image().resize((int(BASE_W*disp_scale), int(BASE_H*disp_scale)), Image.NEAREST)
    sbuf = io.BytesIO(); stats_img.save(sbuf, format="PNG"); stats_png = sbuf.getvalue()
    st.image(stats_png, caption="最終着弾の割合（ホーム/ビジター別）")
    st.download_button("統計画像をPNGでダウンロード", data=stats_png,
                       file_name=f"game{S.game_number}_stats.png", mime="image/png")

    if S.final_positions:
        cnt = Counter(S.final_positions)
        ranked = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
        st.markdown("#### ミスランキング（最終着弾の多い順）")
        for rank, (pos, c) in enumerate(ranked, start=1):
            pos_clean = pos.replace("\n", " ")
            st.write(f"{rank}. {pos_clean} — {c} 回")
    else:
        st.info("まだ最終着弾データがありません。")
