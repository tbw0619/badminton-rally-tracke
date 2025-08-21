import io
from collections import Counter
import math

from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ===== Page config (安全ガード) =====
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

# ====== 余白圧縮 & 小型ボタン ======
st.markdown("""
<style>
.block-container{padding-top:0.35rem;padding-bottom:0.35rem;max-width:1500px}
[data-testid="stHeader"]{height:2rem}
div.stButton>button{padding:2px 4px;font-size:11px;line-height:1.1;height:24px;min-height:24px}
[data-testid="column"]{padding-top:0rem;padding-bottom:0rem}
h3, h4 { margin-top:0.4rem; margin-bottom:0.4rem; }
</style>
""", unsafe_allow_html=True)

st.title("🏸 Badminton Rally Tracker — Web版")

# ====== 定数（ベース座標・色） ======
GRID_ROWS = 5
GRID_COLS = 5
BASE_W = 390     # 400*1.1 に近い縦横比を簡略化
BASE_H = 740
MID_Y  = BASE_H // 2

HOME_STR = "ホーム"
VIS_STR  = "ビジター"

GREEN        = (0,128,0)
GREEN_HOME   = (34,139,34)   # 背景（ホーム面）
GREEN_VIS    = (30,110,30)   # 背景（ビジター面）
WHITE        = (255,255,255)
RED          = (220,20,60)
BLUE         = (30,144,255)
YELLOW       = (255,215,0)

try:
    FONT = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT = ImageFont.load_default()

# ====== セッション ======
S = st.session_state
if "rallies" not in S:        # ラリー履歴（各ラリーは[(x,y),...]。座標はベース画像基準）
    S.rallies = []
if "current" not in S:        # 入力中ラリー
    S.current = []
if "scores" not in S:
    S.scores = {"home": 0, "visitor": 0}

# ====== 座標/セルユーティリティ ======
def cell_center(col: int, row: int, top_half: bool) -> tuple[int,int]:
    """グリッド(1..5,1..5)のセル中心（ベース座標）"""
    cell_w = BASE_W / GRID_COLS
    cell_h = (BASE_H/2) / GRID_ROWS
    x = int((col-0.5) * cell_w)
    if top_half:
        y = int((row-0.5) * cell_h)                 # 上半分(ホーム)
    else:
        y = int(MID_Y + (row-0.5) * cell_h)         # 下半分(ビジター)
    return x, y

def nearest_cell(x: int, y: int) -> tuple[str,int,int]:
    """点が属するサイドと最寄りセル(1..5,1..5)を返す"""
    top_half = y < MID_Y
    coat = HOME_STR if top_half else VIS_STR
    # 列・行を丸める
    cell_w = BASE_W / GRID_COLS
    cell_h = (BASE_H/2) / GRID_ROWS
    c = max(1, min(GRID_COLS, int(x // cell_w + 1)))
    r = max(1, min(GRID_ROWS, int((y if top_half else (y - MID_Y)) // cell_h + 1)))
    return coat, r, c

# ====== コート描画（Pillow） ======
def draw_court_base(img: Image.Image, face_color=GREEN):
    d = ImageDraw.Draw(img)
    d.rectangle((0,0,BASE_W-1,BASE_H-1), fill=face_color, outline=face_color)
    # センターライン
    d.line((0, MID_Y, BASE_W, MID_Y), fill=WHITE, width=2)
    # インナー矩形（両面共通）
    margin_x = int(BASE_W*0.12); margin_y_top = int(BASE_H*0.08); margin_y_bottom = int(BASE_H*0.08)
    d.rectangle((margin_x, margin_y_top, BASE_W-margin_x, MID_Y-margin_y_top), outline=WHITE, width=2)
    d.rectangle((margin_x, MID_Y+margin_y_bottom, BASE_W-margin_x, BASE_H-margin_y_bottom), outline=WHITE, width=2)

def render_traj(paths=None, show_steps=True) -> Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    draw_court_base(img, GREEN)
    if paths:
        d = ImageDraw.Draw(img)
        for i, (x,y) in enumerate(paths):
            # 点
            d.ellipse((x-5,y-5,x+5,y+5), fill=YELLOW)
            if i>0:
                x0,y0 = paths[i-1]
                # サイド遷移で色替え（ホーム->青／ビジター->赤）
                prev_top = y0 < MID_Y
                now_top  = y  < MID_Y
                color = RED if now_top else BLUE
                if prev_top != now_top:
                    color = BLUE if now_top else RED
                d.line((x0,y0,x,y), fill=color, width=2)
                # 矢印頭
                ang = math.atan2(y-y0, x-x0)
                L = 8
                p1 = (x + L*math.cos(ang+2.6), y + L*math.sin(ang+2.6))
                p2 = (x + L*math.cos(ang-2.6), y + L*math.sin(ang-2.6))
                d.polygon([p1,(x,y),p2], fill=color)
                if show_steps:
                    mx,my = (x0+x)/2, (y0+y)/2
                    d.text((mx, my-10 if now_top else my+10), str(i+1), fill=WHITE, font=FONT, anchor="mm")
    return img

def render_stats_from_rallies(rallies) -> Image.Image:
    """各ラリーの最終点のみを集計し、セルごとに％表示"""
    # カウント
    counter = Counter()
    total_home = total_vis = 0
    for rally in rallies:
        if not rally: continue
        x,y = rally[-1]
        coat, r, c = nearest_cell(x,y)
        key = (coat, r, c)
        counter[key] += 1
        if coat == HOME_STR: total_home += 1
        else: total_vis += 1

    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    draw_court_base(img, GREEN)
    d = ImageDraw.Draw(img)
    # ホーム／ビジター別で％表示
    for r in range(1, GRID_ROWS+1):
        for c in range(1, GRID_COLS+1):
            # ホーム
            cnt = counter.get((HOME_STR, r, c), 0)
            pct = (cnt/total_home*100) if total_home else 0
            x,y = cell_center(c, r, top_half=True)
            d.text((x,y), f"{pct:.1f}%", fill=RED, font=FONT, anchor="mm")
            # ビジター
            cnt = counter.get((VIS_STR, r, c), 0)
            pct = (cnt/total_vis*100) if total_vis else 0
            x,y = cell_center(c, r, top_half=False)
            d.text((x,y), f"{pct:.1f}%", fill=BLUE, font=FONT, anchor="mm")
    return img

def render_button_background(face_color) -> Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H//2), face_color)
    # 片面だけ描く
    d = ImageDraw.Draw(img)
    margin_x = int(BASE_W*0.12); margin_y = int((BASE_H//2)*0.08)
    d.rectangle((0,0,BASE_W-1,BASE_H//2-1), outline=face_color, fill=face_color)
    d.rectangle((margin_x, margin_y, BASE_W-margin_x, BASE_H//2-margin_y), outline=WHITE, width=2)
    return img

# ====== 状態更新ヘルパ ======
def add_point_by_cell(is_home: bool, row: int, col: int):
    x,y = cell_center(col, row, top_half=is_home)
    S.current.append((x,y))

def end_rally():
    if S.current:
        S.rallies.append(S.current[:])
        S.current = []
        S.scores["home"] += 1  # （スコア計算は必要に応じて差し替え）

def undo_one():
    if S.current:
        S.current.pop()

def undo_last_rally():
    if S.rallies:
        S.current = S.rallies.pop()

def reset_all():
    S.current = []
    S.rallies = []
    S.scores = {"home":0, "visitor":0}

# ====== レイアウト：3カラム（ボタン先に処理→左/中央描画） ======
col1, col2, col3 = st.columns([1,1,1], gap="small")

# 右：ボタン面（背景にコート画像を敷く）
with col3:
    st.subheader("ボタン", divider="gray")

    # 背景(ホーム)
    bg_home = render_button_background(GREEN_HOME).resize((int(BASE_W*0.9), int((BASE_H//2)*0.9)))
    st.image(bg_home, use_column_width=False)
    st.markdown("**ホーム**")
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            if cols[c-1].button(f"H{r},{c}", key=f"H-{r}-{c}"):
                add_point_by_cell(True, r, c)

    # 背景(ビジター)
    bg_vis = render_button_background(GREEN_VIS).resize((int(BASE_W*0.9), int((BASE_H//2)*0.9)))
    st.image(bg_vis, use_column_width=False)
    st.markdown("**ビジター**")
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            if cols[c-1].button(f"V{r},{c}", key=f"V-{r}-{c}"):
                add_point_by_cell(False, r, c)

    st.divider()
    c1, c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):  end_rally()
    if c2.button("元に戻す", use_container_width=True):    undo_one()

    c3, c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True):    reset_all()

# 左：軌跡
with col1:
    st.subheader("軌跡", divider="gray")
    traj_img = render_traj(S.current, show_steps=True)
    disp = traj_img.resize((int(BASE_W*0.9), int(BASE_H*0.9)))
    st.image(disp, use_column_width=False)

# 中央：統計（各ラリー最終点の分布％）
with col2:
    st.subheader("統計", divider="gray")
    stats_img = render_stats_from_rallies(S.rallies).resize((int(BASE_W*0.9), int(BASE_H*0.9)))
    st.image(stats_img, use_column_width=False)

# スコア
st.markdown(f"**スコア:** ホーム {S.scores['home']} - ビジター {S.scores['visitor']}")
