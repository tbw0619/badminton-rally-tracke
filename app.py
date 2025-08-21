import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ========== Page config & compact UI ==========
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

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

# ========== Constants (4x5) ==========
GRID_ROWS = 4
GRID_COLS = 5

# 描画ベースサイズ（画像はこの解像度で作ってから縮小表示）
BASE_W = 440       # 400*1.1 に近い幅
BASE_H = 748       # 680*1.1 に近い高さ
MID_Y  = int(BASE_H * (329/ (680*1.1)))  # 元コード相当のセンターライン位置

HOME_STR = "ホーム"
VIS_STR  = "ビジター"

GREEN      = (0,128,0)
GREEN_H    = (34,139,34)   # 右のホーム面背景
GREEN_V    = (30,110,30)   # 右のビジター面背景
WHITE      = (255,255,255)
RED        = (220,20,60)
BLUE       = (30,144,255)
YELLOW     = (255,215,0)

try:
    FONT = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT = ImageFont.load_default()

# out 判定（元ロジック）
HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}

def is_out(coat:str, r:int, c:int)->bool:
    return (r,c) in (HOME_OUTS if coat==HOME_STR else VIS_OUTS)

# ========== Session ==========
S = st.session_state
if "rallies" not in S:  S.rallies = []     # 各ラリー: [(x,y),...]
if "current" not in S:  S.current = []     # 入力中ラリー
if "scores"  not in S:  S.scores = {"home":0, "visitor":0}
if "home"    not in S:  S.home = HOME_STR
if "visitor" not in S:  S.visitor = VIS_STR

# ========== Geometry helpers ==========
def cell_size_half():
    cw = BASE_W / GRID_COLS
    ch = (BASE_H/2) / GRID_ROWS
    return cw, ch

def cell_center(col:int, row:int, top_half:bool)->tuple[int,int]:
    cw, ch = cell_size_half()
    x = int((col-0.5)*cw)
    y = int((row-0.5)*ch) if top_half else int(MID_Y + (row-0.5)*ch)
    return x, y

def nearest_cell(x:int, y:int):
    top = y < MID_Y
    cw, ch = cell_size_half()
    c = max(1, min(GRID_COLS, int(x // cw + 1)))
    r = max(1, min(GRID_ROWS, int((y if top else (y - MID_Y)) // ch + 1)))
    return (HOME_STR if top else VIS_STR), r, c

# ========== Drawing ==========
def draw_full_court(img:Image.Image):
    """左/中央用：上下半面＋センター線＋内枠（元アプリ風）"""
    d = ImageDraw.Draw(img)
    # 塗り
    d.rectangle((0,0,BASE_W-1,BASE_H-1), fill=GREEN, outline=GREEN)
    # センター
    d.line((0, MID_Y, BASE_W, MID_Y), fill=WHITE, width=2)
    # インナー長方形（元コード相当）
    x1 = int((11 + 1 * 76) * 1.1)
    y1 = int((11 + 1 * 76) * 1.1)
    x2 = int((11 + 4 * 76) * 1.1)
    y2 = int((346 + 3 * 76) * 1.1)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)

def draw_grid_lines(img:Image.Image, top_half:bool, include_inner=False, face=None):
    """右のボタン背景や左/中央の補助線用：半面に 4x5 グリッド線を引く"""
    d = ImageDraw.Draw(img)
    if face is not None:
        if top_half:
            d.rectangle((0,0,BASE_W-1,MID_Y-1), fill=face, outline=face)
        else:
            d.rectangle((0,MID_Y,BASE_W-1,BASE_H-1), fill=face, outline=face)
    y0,y1 = (0, MID_Y-1) if top_half else (MID_Y, BASE_H-1)
    # 外枠
    d.rectangle((0,y0,BASE_W-1,y1), outline=WHITE, width=2)
    # 格子（縦4・横3）
    cw, ch = cell_size_half()
    for k in range(1, GRID_COLS):
        x = int(k*cw); d.line((x,y0,x,y1), fill=WHITE, width=1)
    for k in range(1, GRID_ROWS):
        y = int(y0 + k*ch); d.line((0,y,BASE_W,y), fill=WHITE, width=1)
    # 内側サービス矩形（薄め）
    if include_inner:
        mx = int(BASE_W*0.12); my = int((BASE_H/2)*0.1)
        d.rectangle((mx, y0+my, BASE_W-mx, y1-my), outline=WHITE, width=2)

def render_traj(paths)->Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H))
    draw_full_court(img)
    d = ImageDraw.Draw(img)
    if paths:
        for i,(x,y) in enumerate(paths):
            d.ellipse((x-5,y-5,x+5,y+5), fill=YELLOW)
            if i>0:
                x0,y0 = paths[i-1]
                prev_top, now_top = (y0<MID_Y), (y<MID_Y)
                color = BLUE if now_top else RED
                if prev_top != now_top: color = RED if now_top else BLUE
                d.line((x0,y0,x,y), fill=color, width=2)
                ang = math.atan2(y-y0, x-x0); L=8
                p1=(x+L*math.cos(ang+2.6), y+L*math.sin(ang+2.6))
                p2=(x+L*math.cos(ang-2.6), y+L*math.sin(ang-2.6))
                d.polygon([p1,(x,y),p2], fill=color)
                mx,my=(x0+x)/2,(y0+y)/2
                d.text((mx, my-10 if now_top else my+10), str(i+1), fill=WHITE, font=FONT, anchor="mm")
    return img

def render_stats(rallies)->Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H))
    draw_full_court(img)
    # ％表示は最終着弾セルで集計
    counter = Counter()
    thome = tvis = 0
    for rally in rallies:
        if not rally: continue
        x,y = rally[-1]
        coat,r,c = nearest_cell(x,y)
        counter[(coat,r,c)] += 1
        if coat==HOME_STR: thome += 1
        else: tvis += 1
    d = ImageDraw.Draw(img)
    for r in range(1, GRID_ROWS+1):
        for c in range(1, GRID_COLS+1):
            # ホーム面
            cnt = counter.get((HOME_STR,r,c),0)
            pct = (cnt/thome*100) if thome else 0
            x,y = cell_center(c,r,True)
            d.text((x,y), f"{pct:.1f}%", fill=RED if S.home==HOME_STR else BLUE, font=FONT, anchor="mm")
            # ビジター面
            cnt = counter.get((VIS_STR,r,c),0)
            pct = (cnt/tvis*100) if tvis else 0
            x,y = cell_center(c,r,False)
            d.text((x,y), f"{pct:.1f}%", fill=BLUE if S.visitor==VIS_STR else RED, font=FONT, anchor="mm")
    # 格子を重ねて視認性を上げる
    draw_grid_lines(img, True)
    draw_grid_lines(img, False)
    return img

def half_background(face)->Image.Image:
    """右カラム：ホーム/ビジターのボタン背景。半面＋白い格子を描く。"""
    img = Image.new("RGB", (BASE_W, BASE_H))
    # 上半面のみ使う
    draw_grid_lines(img, True, include_inner=True, face=face)
    return img.crop((0,0,BASE_W,MID_Y))

# ========== Actions ==========
def add_point(coat:str, r:int, c:int):
    x,y = cell_center(c,r, coat==HOME_STR)
    S.current.append((x,y))

def end_rally():
    if S.current:
        S.rallies.append(S.current[:])
        S.current = []
        S.scores["home"] += 1  # 必要に応じてスコアロジック置換

def undo_one():
    if S.current: S.current.pop()

def undo_last_rally():
    if S.rallies:
        S.current = S.rallies.pop()

def reset_all():
    S.current = []; S.rallies = []; S.scores = {"home":0, "visitor":0}

# ========== Layout ==========
col1, col2, col3 = st.columns([1,1,1], gap="small")

# 右：ボタン（背景に白い格子線）
with col3:
    st.subheader("ボタン", divider="gray")

    # --- ホーム ---
    st.markdown("**ホーム**")
    bg_home = half_background(GREEN_H).resize((int(BASE_W*0.9), int(MID_Y*0.9)))
    st.image(bg_home, use_column_width=False)
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            prefix = "o" if is_out(HOME_STR, r, c) else ""
            lbl = f"{prefix}H{r},{c}"
            if cols[c-1].button(lbl, key=f"H-{r}-{c}"):
                add_point(HOME_STR, r, c)

    # --- ビジター ---
    st.markdown("**ビジター**")
    bg_vis = half_background(GREEN_V).resize((int(BASE_W*0.9), int(MID_Y*0.9)))
    st.image(bg_vis, use_column_width=False)
    for r in range(1, GRID_ROWS+1):
        cols = st.columns(GRID_COLS, gap="small")
        for c in range(1, GRID_COLS+1):
            prefix = "o" if is_out(VIS_STR, r, c) else ""
            lbl = f"{prefix}V{r},{c}"
            if cols[c-1].button(lbl, key=f"V-{r}-{c}"):
                add_point(VIS_STR, r, c)

    st.divider()
    c1,c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):  end_rally()
    if c2.button("元に戻す", use_container_width=True):    undo_one()
    c3,c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True):    reset_all()

# 左：軌跡（元の見た目＋4×5）
with col1:
    st.subheader("軌跡", divider="gray")
    traj = render_traj(S.current)
    st.image(traj.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

# 中央：統計（最終着弾を%表示＋4×5格子）
with col2:
    st.subheader("統計", divider="gray")
    stats = render_stats(S.rallies)
    st.image(stats.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

# スコア
st.markdown(f"**スコア:** ホーム {S.scores['home']} - ビジター {S.scores['visitor']}")
