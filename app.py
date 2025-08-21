# app.py  —  Streamlit + Pillow（matplotlib不要）
import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# -------- page config & compact UI --------
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
/* ボタングリッドの白線（縦線/横線） */
.grid-vline{background:#fff;height:24px;border-radius:1px}
.grid-hline{background:#fff;height:4px;margin:2px 0;border-radius:2px}
.section-spacer{height:6px}
</style>
""", unsafe_allow_html=True)

st.title("🏸 Badminton Rally Tracker — Web版")

# -------- constants (4x5 court) --------
GRID_ROWS = 4
GRID_COLS = 5
BASE_W = 440
BASE_H = 748
MID_Y  = int(BASE_H * (329/(680*1.1)))  # 元コード比

HOME_STR = "ホーム"
VIS_STR  = "ビジター"

GREEN      = (0,128,0)
WHITE      = (255,255,255)
RED        = (220,20,60)
BLUE       = (30,144,255)
YELLOW     = (255,215,0)

try:
    FONT = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT = ImageFont.load_default()

# 元ロジックの out セル
HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}

def is_out(coat:str, r:int, c:int)->bool:
    return (r,c) in (HOME_OUTS if coat==HOME_STR else VIS_OUTS)

# -------- session --------
S = st.session_state
if "rallies" not in S:  S.rallies = []       # 各ラリー: [(x,y),...]
if "current" not in S:  S.current = []       # 入力中
if "scores"  not in S:  S.scores  = {"home":0,"visitor":0}

# -------- geometry helpers --------
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

# -------- drawing (Pillow) --------
def draw_full_court(img:Image.Image):
    d = ImageDraw.Draw(img)
    d.rectangle((0,0,BASE_W-1,BASE_H-1), fill=GREEN, outline=GREEN)
    # mid line
    d.line((0, MID_Y, BASE_W, MID_Y), fill=WHITE, width=2)
    # inner rectangle（元Tkinter座標に合わせ）
    x1 = int((11 + 1 * 76) * 1.1)
    y1 = int((11 + 1 * 76) * 1.1)
    x2 = int((11 + 4 * 76) * 1.1)
    y2 = int((346 + 3 * 76) * 1.1)
    d.rectangle((x1, y1, x2, y2), outline=WHITE, width=2)

def render_traj(paths)->Image.Image:
    img = Image.new("RGB", (BASE_W, BASE_H))
    draw_full_court(img)
    if paths:
        d = ImageDraw.Draw(img)
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
            cnt = counter.get((HOME_STR,r,c),0)
            pct = (cnt/thome*100) if thome else 0
            x,y = cell_center(c,r,True)
            d.text((x,y), f"{pct:.1f}%", fill=RED, font=FONT, anchor="mm")
            cnt = counter.get((VIS_STR,r,c),0)
            pct = (cnt/tvis*100) if tvis else 0
            x,y = cell_center(c,r,False)
            d.text((x,y), f"{pct:.1f}%", fill=BLUE, font=FONT, anchor="mm")
    return img

# -------- state actions --------
def add_point(coat:str, r:int, c:int):
    x,y = cell_center(c,r, coat==HOME_STR)
    S.current.append((x,y))

def end_rally():
    if S.current:
        S.rallies.append(S.current[:])
        S.current = []
        S.scores["home"] += 1  # 必要に応じて差し替え

def undo_one():
    if S.current: S.current.pop()

def undo_last_rally():
    if S.rallies:
        S.current = S.rallies.pop()

def reset_all():
    S.current = []; S.rallies = []; S.scores = {"home":0,"visitor":0}

# -------- layout --------
col1, col2, col3 = st.columns([1,1,1], gap="large")

# 右：ボタン（背景画像は出さず、白い線だけをUI上で描く）
def render_button_grid(title:str, coat:str, key_prefix:str):
    st.markdown(f"**{title}**")

    # 1行ずつ： [btn, vline, btn, vline, ... btn] の9カラムで作る
    for r in range(1, GRID_ROWS+1):
        # 9カラム（5ボタン＋4縦線）— 比率を小さくして“線”を細く
        ratios = [9,1,9,1,9,1,9,1,9]
        cols = st.columns(ratios, gap="small")
        for c in range(1, GRID_COLS+1):
            prefix = "o" if is_out(coat, r, c) else ""
            label  = f"{prefix}{'H' if coat==HOME_STR else 'V'}{r},{c}"
            if cols[(c-1)*2].button(label, key=f"{key_prefix}-{r}-{c}"):
                add_point(coat, r, c)
            # 縦線はボタンの右側に（最終列以外）
            if c < GRID_COLS:
                with cols[(c-1)*2+1]:
                    st.markdown('<div class="grid-vline"></div>', unsafe_allow_html=True)
        # 行の下に横線（最終行は描かない）
        if r < GRID_ROWS:
            st.markdown('<div class="grid-hline"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

with col3:
    st.subheader("ボタン", divider="gray")
    render_button_grid("ホーム", HOME_STR, "H")
    render_button_grid("ビジター", VIS_STR, "V")

    c1,c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):  end_rally()
    if c2.button("元に戻す", use_container_width=True):    undo_one()
    c3,c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True):    reset_all()

with col1:
    st.subheader("軌跡", divider="gray")
    traj = render_traj(S.current)
    st.image(traj.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

with col2:
    st.subheader("統計", divider="gray")
    stats = render_stats(S.rallies)
    st.image(stats.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

st.markdown(f"**スコア:** ホーム {S.scores['home']} - ビジター {S.scores['visitor']}")
