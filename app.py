import io
from collections import Counter
import math

from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ===== Page config（失敗時も続行） =====
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

# ===== 余白圧縮 & 小型ボタン =====
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

# ===== 定数（ベース座標・色） =====
GRID_ROWS = 5
GRID_COLS = 5
BASE_W = 390
BASE_H = 740
MID_Y  = BASE_H // 2

HOME_STR = "ホーム"
VIS_STR  = "ビジター"

GREEN        = (0,128,0)
GREEN_HOME   = (34,139,34)   # 背景（ホーム半面）
GREEN_VIS    = (30,110,30)   # 背景（ビジター半面）
WHITE        = (255,255,255)
RED          = (220,20,60)
BLUE         = (30,144,255)
YELLOW       = (255,215,0)

try:
    FONT = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT = ImageFont.load_default()

# ===== セッション =====
S = st.session_state
if "rallies" not in S: S.rallies = []      # 各ラリー: [(x,y),...]
if "current" not in S: S.current = []      # 入力中ラリー
if "scores"  not in S: S.scores  = {"home":0, "visitor":0}

# ===== ユーティリティ =====
def cell_size():
    cell_w = BASE_W / GRID_COLS
    cell_h = (BASE_H/2) / GRID_ROWS
    return cell_w, cell_h

def cell_center(col: int, row: int, top_half: bool) -> tuple[int,int]:
    cw, ch = cell_size()
    x = int((col-0.5) * cw)
    y = int((row-0.5) * ch) if top_half else int(MID_Y + (row-0.5) * ch)
    return x, y

def nearest_cell(x: int, y: int) -> tuple[str,int,int]:
    top_half = y < MID_Y
    coat = HOME_STR if top_half else VIS_STR
    cw, ch = cell_size()
    c = max(1, min(GRID_COLS, int(x // cw + 1)))
    r = max(1, min(GRID_ROWS, int((y if top_half else (y - MID_Y)) // ch + 1)))
    return coat, r, c

# ===== コート描画（Pillow） =====
def draw_half_court_grid(img: Image.Image, top_half: bool, face_color, with_inner_rect=True):
    """半面に外枠＋5×5グリッド線を引く（ボタン面背景用）。"""
    d = ImageDraw.Draw(img)
    # 塗りつぶし
    if top_half:
        d.rectangle((0,0,BASE_W-1, MID_Y-1), fill=face_color, outline=face_color)
    else:
        d.rectangle((0,MID_Y,BASE_W-1,BASE_H-1), fill=face_color, outline=face_color)

    # 外枠
    y0, y1 = (0, MID_Y-1) if top_half else (MID_Y, BASE_H-1)
    d.rectangle((0, y0, BASE_W-1, y1), outline=WHITE, width=2)

    # 5×5 グリッド
    cw, ch = cell_size()
    # 縦線（列の境目 1..4）
    for k in range(1, GRID_COLS):
        x = int(k * cw)
        d.line((x, y0, x, y1), fill=WHITE, width=1)
    # 横線（行の境目 1..4）
    for k in range(1, GRID_ROWS):
        y = int(y0 + k * ch)
        d.line((0, y, BASE_W, y), fill=WHITE, width=1)

    # 任意：内側サービス矩形（視認性のため軽く）
    if with_inner_rect:
        margin_x = int(BASE_W*0.12)
        margin_y = int((BASE_H/2)*0.12)
        d.rectangle((margin_x, y0+margin_y, BASE_W-margin_x, y1-margin_y), outline=WHITE, width=2)

def render_traj(paths=None, show_steps=True) -> Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    d = ImageDraw.Draw(img)
    # 背景：上下半面を塗って線を描く
    draw_half_court_grid(img, True,  GREEN)
    draw_half_court_grid(img, False, GREEN)
    # センターライン
    d.line((0, MID_Y, BASE_W, MID_Y), fill=WHITE, width=2)

    if paths:
        for i, (x,y) in enumerate(paths):
            d.ellipse((x-5,y-5,x+5,y+5), fill=YELLOW)
            if i>0:
                x0,y0 = paths[i-1]
                prev_top = (y0 < MID_Y)
                now_top  = (y  < MID_Y)
                color = BLUE if now_top else RED
                if prev_top != now_top:
                    color = RED if now_top else BLUE
                d.line((x0,y0,x,y), fill=color, width=2)
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
    counter = Counter()
    total_home = total_vis = 0
    for rally in rallies:
        if not rally: continue
        x,y = rally[-1]
        coat, r, c = nearest_cell(x,y)
        counter[(coat,r,c)] += 1
        if coat == HOME_STR: total_home += 1
        else: total_vis += 1

    img = Image.new("RGB", (BASE_W, BASE_H), GREEN)
    draw_half_court_grid(img, True,  GREEN)   # 上半面
    draw_half_court_grid(img, False, GREEN)   # 下半面
    d = ImageDraw.Draw(img)
    # ％をセル中心に描画
    for r in range(1, GRID_ROWS+1):
        for c in range(1, GRID_COLS+1):
            cnt = counter.get((HOME_STR, r, c), 0)
            pct = (cnt/total_home*100) if total_home else 0
            x,y = cell_center(c, r, top_half=True)
            d.text((x,y), f"{pct:.1f}%", fill=RED, font=FONT, anchor="mm")
            cnt = counter.get((VIS_STR, r, c), 0)
            pct = (cnt/total_vis*100) if total_vis else 0
            x,y = cell_center(c, r, top_half=False)
            d.text((x,y), f"{pct:.1f}%", fill=BLUE, font=FONT, anchor="mm")
    return img

def render_half_background(face_color) -> Image.Image:
    """ボタン面の背景（半面のみ、5×5グリッド付き）"""
    img = Image.new("RGB", (BASE_W, BASE_H), face_color)
    draw_half_court_grid(img, True, face_color)   # 上半面のみ使う
    return img.crop((0,0,BASE_W,MID_Y))

# ===== 状態更新 =====
def add_point_by_cell(is_home: bool, row: int, col: int):
    x,y = cell_center(col, row, top_half=is_home)
    S.current.append((x,y))

def end_rally():
    if S.current:
        S.rallies.append(S.current[:])
        S.current = []
        S.scores["home"] += 1  # 必要に応じてスコアロジック差し替え

def undo_one():
    if S.current: S.current.pop()

def undo_last_rally():
    if S.rallies:
        S.current = S.rallies.pop()

def reset_all():
    S.current = []
    S.rallies = []
    S.scores = {"home":0, "visitor":0}

# ===== レイアウト：3カラム（右の入力→左/中央描画） =====
col1, col2, col3 = st.columns([1,1,1], gap="small")

with col3:
    st.subheader("ボタン", divider="gray")

    # --- ホーム面：背景に半面コート（5×5白グリッド） ---
    bg_home = render_half_background(GREEN_HOME).resize((int(BASE_W*0.9), int(MID_Y*0.9)))
    st.image(bg_home, use_column_width=False)
    st.markdown("**ホーム**")
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            # 画像のような「oH1,1」表記（境界セルを 'o' プレフィックス）に近づける例
            is_outer = (r in {1,GRID_ROWS}) or (c in {1,GRID_COLS})
            lbl = f"{'o' if is_outer else ''}H{r},{c}"
            if cols[c-1].button(lbl, key=f"H-{r}-{c}"):
                add_point_by_cell(True, r, c)

    # --- ビジター面 ---
    bg_vis = render_half_background(GREEN_VIS).resize((int(BASE_W*0.9), int(MID_Y*0.9)))
    st.image(bg_vis, use_column_width=False)
    st.markdown("**ビジター**")
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            is_outer = (r in {1,GRID_ROWS}) or (c in {1,GRID_COLS})
            lbl = f"{'o' if is_outer else ''}V{r},{c}"
            if cols[c-1].button(lbl, key=f"V-{r}-{c}"):
                add_point_by_cell(False, r, c)

    st.divider()
    c1, c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):  end_rally()
    if c2.button("元に戻す", use_container_width=True):    undo_one()

    c3, c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True):    reset_all()

with col1:
    st.subheader("軌跡", divider="gray")
    traj_img = render_traj(S.current, show_steps=True)
    st.image(traj_img.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

with col2:
    st.subheader("統計", divider="gray")
    stats_img = render_stats_from_rallies(S.rallies)
    st.image(stats_img.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

st.markdown(f"**スコア:** ホーム {S.scores['home']} - ビジター {S.scores['visitor']}")
