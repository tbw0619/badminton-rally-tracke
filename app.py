# app.py — Streamlit + Pillow（matplotlib不要）
import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# ---------- Page config & compact UI ----------
try:
    st.set_page_config(page_title="Badminton Rally Tracker", page_icon="🏸", layout="wide")
except Exception:
    pass

st.markdown("""
<style>
.block-container{padding-top:0.35rem;padding-bottom:0.35rem;max-width:1500px}
[data-testid="stHeader"]{height:2rem}
div.stButton>button{padding:2px 6px;font-size:11px;line-height:1.1;height:24px;min-height:24px}
[data-testid="column"]{padding-top:0rem;padding-bottom:0rem}
h3, h4 { margin-top:0.4rem; margin-bottom:0.4rem; }

/* ホームとビジターの間だけの横線（一本） */
.hr-between {
  width: 100%;
  height: 4px;
  background: #fff;
  margin: 6px 0 10px 0;
  border-radius: 3px;
}

/* ボタン群の“内側だけ”に引く白い線 */
.grid-vline{width:2px;height:24px;background:#ffffff;border-radius:2px;margin:0 2px;}
.grid-hline{width:100%;height:2px;background:#ffffff;border-radius:2px;margin:6px 0;}
</style>
""", unsafe_allow_html=True)

st.title("🏸 Badminton Rally Tracker — Web版")

# ---------- 定数（4×5） ----------
GRID_ROWS = 4
GRID_COLS = 5
BASE_W = 440
BASE_H = 748

# もともとのセンター（元Tkinter比率）
_BASE_MID_Y  = int(BASE_H * (329/(680*1.1)))

# ▼中央線を少し下げる量（セル高さの割合）例: 0.12=12%
MID_SHIFT_RATIO = 0.25
_CELL_H = (BASE_H/2) / GRID_ROWS
MID_Y = _BASE_MID_Y + int(_CELL_H * MID_SHIFT_RATIO)

HOME_STR = "ホーム"
VIS_STR  = "ビジター"

GREEN = (0,128,0); WHITE=(255,255,255); RED=(220,20,60); BLUE=(30,144,255); YELLOW=(255,215,0)

try:
    FONT = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    FONT = ImageFont.load_default()

# out セル（元ロジック）
HOME_OUTS = {(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(3,1),(4,1),(2,5),(3,5),(4,5)}
VIS_OUTS  = {(1,1),(1,5),(2,1),(2,5),(3,1),(3,5),(4,1),(4,2),(4,3),(4,4),(4,5)}
def is_out(coat:str, r:int, c:int)->bool:
    return (r,c) in (HOME_OUTS if coat==HOME_STR else VIS_OUTS)

# ---------- Session ----------
S = st.session_state
if "rallies" not in S:  S.rallies = []       # 各ラリー: [(x,y),...]
if "current" not in S:  S.current = []       # 入力中ラリー
if "scores"  not in S:  S.scores  = {"home":0,"visitor":0}

# ---------- Geometry ----------
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

# ---------- Drawing（左：軌跡／中央：統計） ----------
def draw_full_court(img:Image.Image):
    d = ImageDraw.Draw(img)
    d.rectangle((0,0,BASE_W-1,BASE_H-1), fill=GREEN, outline=GREEN)
    # mid line
    d.line((0, MID_Y, BASE_W, MID_Y), fill=WHITE, width=2)
    # inner rectangle（元Tkinter座標）
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
                color = (BLUE if now_top else RED) if prev_top==now_top else (RED if now_top else BLUE)
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
    counter = Counter(); thome=tvis=0
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
            cnt = counter.get((HOME_STR,r,c),0); pct = (cnt/thome*100) if thome else 0
            x,y = cell_center(c,r,True);  d.text((x,y), f"{pct:.1f}%", fill=RED,  font=FONT, anchor="mm")
            cnt = counter.get((VIS_STR ,r,c),0); pct = (cnt/tvis *100) if tvis  else 0
            x,y = cell_center(c,r,False); d.text((x,y), f"{pct:.1f}%", fill=BLUE, font=FONT, anchor="mm")
    return img

# ---------- State actions ----------
def add_point(coat:str, r:int, c:int):
    x,y = cell_center(c,r, coat==HOME_STR)
    S.current.append((x,y))

def end_rally():
    if S.current:
        S.rallies.append(S.current[:])
        S.current = []
        S.scores["home"] += 1   # 必要ならロジック置換

def undo_one():
    if S.current: S.current.pop()

def undo_last_rally():
    if S.rallies:
        S.current = S.rallies.pop()

def reset_all():
    S.current = []; S.rallies = []; S.scores = {"home":0,"visitor":0}

# ---------- Buttons UI（白い線を引く） ----------
def render_button_grid(title: str, coat: str, key_prefix: str):
    """4x5ボタンを並べ、中央3x3領域（列2-4・行2-4）を白枠で囲む。
       縦線：列1-2の間と列4-5の間、横線：行1-2の間と行4の下。
    """
    st.markdown(f"**{title}**")

    for r in range(1, GRID_ROWS+1):
        # 7枠: [btn1][vlineL][btn2][btn3][btn4][vlineR][btn5]
        cols = st.columns([9,1,9,9,9,1,9], gap="small")

        # 列1
        prefix = "o" if is_out(coat, r, 1) else ""
        lbl = f"{prefix}{'H' if coat==HOME_STR else 'V'}{r},1"
        if cols[0].button(lbl, key=f"{key_prefix}-{r}-1"):
            add_point(coat, r, 1)

        # 縦線（左辺）
        with cols[1]:
            st.markdown('<div class="grid-vline"></div>', unsafe_allow_html=True)

        # 列2〜4
        for idx, c in enumerate([2,3,4], start=2):
            prefix = "o" if is_out(coat, r, c) else ""
            lbl = f"{prefix}{'H' if coat==HOME_STR else 'V'}{r},{c}"
            if cols[idx].button(lbl, key=f"{key_prefix}-{r}-{c}"):
                add_point(coat, r, c)

        # 縦線（右辺）
        with cols[5]:
            st.markdown('<div class="grid-vline"></div>', unsafe_allow_html=True)

        # 列5
        prefix = "o" if is_out(coat, r, 5) else ""
        lbl = f"{prefix}{'H' if coat==HOME_STR else 'V'}{r},5"
        if cols[6].button(lbl, key=f"{key_prefix}-{r}-5"):
            add_point(coat, r, 5)

       # ホームとビジターで横線の位置を変える
        if coat == "ホーム":
            if r == 1 :  # 行1と行4
                st.markdown('<div class="grid-hline"></div>', unsafe_allow_html=True)
        else:  # ビジター
            if r == 0 or r == 3:  # 行1と行3
                st.markdown('<div class="grid-hline"></div>', unsafe_allow_html=True)

# ---------- Layout ----------
col1, col2, col3 = st.columns([1,1,1], gap="large")

# 右：ボタン（白い線を追加）
with col3:
    st.subheader("ボタン", divider="gray")

    # --- ホーム ---
    render_button_grid("ホーム", HOME_STR, "H")

    # --- ホームとビジターの間の一本線 ---
    st.markdown('<div class="hr-between"></div>', unsafe_allow_html=True)

    # --- ビジター ---
    render_button_grid("ビジター", VIS_STR, "V")

    st.divider()
    c1,c2 = st.columns(2, gap="small")
    if c1.button("ラリー終了", use_container_width=True):  end_rally()
    if c2.button("元に戻す", use_container_width=True):    undo_one()
    c3,c4 = st.columns(2, gap="small")
    if c3.button("一つ前のラリー", use_container_width=True): undo_last_rally()
    if c4.button("ラリー全消去", use_container_width=True):    reset_all()

# 左：軌跡
with col1:
    st.subheader("軌跡", divider="gray")
    traj = render_traj(S.current)
    st.image(traj.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

# 中央：統計
with col2:
    st.subheader("統計", divider="gray")
    stats = render_stats(S.rallies)
    st.image(stats.resize((int(BASE_W*0.9), int(BASE_H*0.9))), use_column_width=False)

st.markdown(f"**スコア:** ホーム {S.scores['home']} - ビジター {S.scores['visitor']}")
