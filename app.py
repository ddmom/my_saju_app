import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, time, date
from korean_lunar_calendar import KoreanLunarCalendar

# 1. 페이지 설정
st.set_page_config(page_title="전문가용 정통 사주 명리학", page_icon="📜", layout="wide")

# ---------------------------------------------------------
# [데이터베이스 초기화]
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('saju_app.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS saju_data (ganji TEXT PRIMARY KEY, meaning TEXT)''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            birth_date TEXT,
            birth_time TEXT,
            gender TEXT
        )
    ''')
    cursor.execute("SELECT count(*) FROM saju_data")
    if cursor.fetchone()[0] == 0:
        cheongan, jiji = list("갑을병정무기경신임계"), list("자축인묘진사오미신유술해")
        saju_list = [(g+j, f"{g+j} 일주 기본 해석") for i in range(60) for g, j in [(cheongan[i%10], jiji[i%12])]]
        cursor.executemany('INSERT INTO saju_data VALUES (?, ?)', saju_list)
        conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# [DB 헬퍼 함수]
# ---------------------------------------------------------
def save_user_profile(name, b_date, b_time, gender):
    conn = sqlite3.connect('saju_app.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO saved_users (name, birth_date, birth_time, gender) VALUES (?, ?, ?, ?)", 
                       (name, str(b_date), str(b_time), gender))
        conn.commit()
        st.toast(f"✅ '{name}'님 정보가 저장되었습니다!")
    except Exception as e:
        st.error(f"저장 실패: {e}")
    conn.close()

def get_saved_users_list():
    conn = sqlite3.connect('saju_app.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM saved_users ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_user_detail(name):
    conn = sqlite3.connect('saju_app.db')
    cursor = conn.cursor()
    cursor.execute("SELECT birth_date, birth_time, gender FROM saved_users WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_user_profile(name):
    conn = sqlite3.connect('saju_app.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_users WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    st.toast(f"🗑️ '{name}'님 정보가 삭제되었습니다.")

# ---------------------------------------------------------
# [계산 로직들]
# ---------------------------------------------------------
GAN_INFO = {
    '갑': ('목', '양'), '을': ('목', '음'), '병': ('화', '양'), '정': ('화', '음'),
    '무': ('토', '양'), '기': ('토', '음'), '경': ('금', '양'), '신': ('금', '음'),
    '임': ('수', '양'), '계': ('수', '음')
}
JI_FOR_TEN_GODS = {
    '자': ('수', '양'), '해': ('수', '음'), '인': ('목', '양'), '묘': ('목', '음'),
    '사': ('화', '양'), '오': ('화', '음'), '신': ('금', '양'), '유': ('금', '음'),
    '진': ('토', '양'), '술': ('토', '양'), '축': ('토', '음'), '미': ('토', '음')
}
ALL_CHAR_MAP = {
    '갑':'목', '을':'목', '인':'목', '묘':'목',
    '병':'화', '정':'화', '사':'화', '오':'화',
    '무':'토', '기':'토', '진':'토', '술':'토', '축':'토', '미':'토',
    '경':'금', '신':'금', '유':'금',
    '임':'수', '계':'수', '해':'수', '자':'수'
}

def get_ten_gods(day_gan, target_char):
    if target_char in GAN_INFO: target_elem, target_yin = GAN_INFO[target_char]
    else: target_elem, target_yin = JI_FOR_TEN_GODS.get(target_char, ('토', '양'))
    day_elem, day_yin = GAN_INFO[day_gan]
    relations = {
        ('목', '목'): '비겁', ('목', '화'): '식상', ('목', '토'): '재성', ('목', '금'): '관성', ('목', '수'): '인성',
        ('화', '화'): '비겁', ('화', '토'): '식상', ('화', '금'): '재성', ('화', '수'): '관성', ('화', '목'): '인성',
        ('토', '토'): '비겁', ('토', '금'): '식상', ('토', '수'): '재성', ('토', '목'): '관성', ('토', '화'): '인성',
        ('금', '금'): '비겁', ('금', '수'): '식상', ('금', '목'): '재성', ('금', '화'): '관성', ('금', '토'): '인성',
        ('수', '수'): '비겁', ('수', '목'): '식상', ('수', '화'): '재성', ('수', '토'): '관성', ('수', '금'): '인성',
    }
    base_rel = relations.get((day_elem, target_elem))
    is_same_yin = (day_yin == target_yin)
    mapping = {'비겁': ('비견', '겁재'), '식상': ('식신', '상관'), '재성': ('편재', '정재'), '관성': ('편관', '정관'), '인성': ('편인', '정인')}
    if base_rel: return mapping[base_rel][0] if is_same_yin else mapping[base_rel][1]
    return ""

def get_12_unseong(day_gan, ji):
    table = {
        '갑': {'해':'장생','자':'목욕','축':'관대','인':'건록','묘':'제왕','진':'쇠','사':'병','오':'사','미':'묘','신':'절','유':'태','술':'양'},
        '을': {'오':'장생','사':'목욕','진':'관대','묘':'건록','인':'제왕','축':'쇠','자':'병','해':'사','술':'묘','유':'절','신':'태','미':'양'},
        '병': {'인':'장생','묘':'목욕','진':'관대','사':'건록','오':'제왕','미':'쇠','신':'병','유':'사','술':'묘','해':'절','자':'태','축':'양'},
        '정': {'유':'장생','신':'목욕','미':'관대','오':'건록','사':'제왕','진':'쇠','묘':'병','인':'사','축':'묘','자':'절','해':'태','술':'양'},
        '무': {'인':'장생','묘':'목욕','진':'관대','사':'건록','오':'제왕','미':'쇠','신':'병','유':'사','술':'묘','해':'절','자':'태','축':'양'},
        '기': {'유':'장생','신':'목욕','미':'관대','오':'건록','사':'제왕','진':'쇠','묘':'병','인':'사','축':'묘','자':'절','해':'태','술':'양'},
        '경': {'사':'장생','오':'목욕','미':'관대','신':'건록','유':'제왕','술':'쇠','해':'병','자':'사','축':'묘','인':'절','묘':'태','진':'양'},
        '신': {'자':'장생','해':'목욕','술':'관대','유':'건록','신':'제왕','미':'쇠','오':'병','사':'사','진':'묘','묘':'절','인':'태','축':'양'},
        '임': {'신':'장생','유':'목욕','술':'관대','해':'건록','자':'제왕','축':'쇠','인':'병','묘':'사','진':'묘','사':'절','오':'태','미':'양'},
        '계': {'묘':'장생','인':'목욕','축':'관대','자':'건록','해':'제왕','술':'쇠','유':'병','신':'사','미':'묘','오':'절','사':'태','진':'양'}
    }
    return table.get(day_gan, {}).get(ji, "")

def get_saju_palja(year, month, day, hour, minute):
    gan_list = list("갑을병정무기경신임계")
    ji_list = list("자축인묘진사오미신유술해")
    adjust_year = year
    if month == 1 or (month == 2 and day < 4): adjust_year = year - 1
    y_idx = (adjust_year - 4) % 60
    year_gan = gan_list[y_idx % 10]
    year_ji = ji_list[y_idx % 12]
    
    if month == 1: month_idx = 11
    elif month == 2:
        if day < 4: month_idx = 11
        else: month_idx = 0
    else:
        if day < 6: month_idx = month - 3
        else: month_idx = month - 2

    y_gan_idx = gan_list.index(year_gan)
    m_start_gan_idx = ((y_gan_idx % 5) + 1) * 2
    month_gan = gan_list[(m_start_gan_idx + month_idx) % 10]
    month_ji = ji_list[(2 + month_idx) % 12] 

    base_date = datetime(1900, 1, 1)
    target_date = datetime(year, month, day)
    days_diff = (target_date - base_date).days
    d_idx = (days_diff + 10) % 60
    day_gan = gan_list[d_idx % 10]
    day_ji = ji_list[d_idx % 12]

    total_minutes = hour * 60 + minute
    if total_minutes >= 23*60 + 30 or total_minutes < 1*60 + 30: time_ji_idx = 0
    else: time_ji_idx = (total_minutes - 90) // 120 + 1
    d_gan_idx = gan_list.index(day_gan)
    time_gan_idx = ((d_gan_idx % 5) * 2 + time_ji_idx) % 10
    time_gan = gan_list[time_gan_idx]
    time_ji = ji_list[time_ji_idx]
    
    return {'year': year_gan+year_ji, 'month': month_gan+month_ji, 'day': day_gan+day_ji, 'time': time_gan+time_ji}

# ---------------------------------------------------------
# [화면 UI 구성]
# ---------------------------------------------------------

# State 초기화
if 'input_date' not in st.session_state: st.session_state.input_date = datetime(1990, 5, 5)
if 'input_time' not in st.session_state: st.session_state.input_time = time(13, 30)
if 'input_gender' not in st.session_state: st.session_state.input_gender = "남성"

# 사이드바
with st.sidebar:
    st.header("📂 명단 관리")
    
    # 1. 초기화 버튼 (NEW!)
    if st.button("🔄 입력 초기화 (새로하기)", use_container_width=True):
        st.session_state.input_date = datetime(1990, 5, 5)
        st.session_state.input_time = time(13, 30)
        st.session_state.input_gender = "남성"
        st.rerun()
        
    st.write("---")
    
    # 2. 저장된 명단 불러오기/삭제
    saved_list = get_saved_users_list()
    selected_user = st.selectbox("명단 선택", ["선택하세요"] + saved_list)
    
    col_s1, col_s2 = st.columns(2)
    if col_s1.button("불러오기"):
        if selected_user != "선택하세요":
            u_data = get_user_detail(selected_user)
            st.session_state.input_date = datetime.strptime(u_data[0], "%Y-%m-%d").date()
            st.session_state.input_time = datetime.strptime(u_data[1], "%H:%M:%S").time()
            st.session_state.input_gender = u_data[2]
            st.rerun()
            
    if col_s2.button("삭제하기"):
        if selected_user != "선택하세요":
            delete_user_profile(selected_user)
            st.rerun()

st.title("📜 전문가용 정통 사주 명리학")

# 메인 입력 폼
with st.container():
    col1, col2, col3 = st.columns([1.5, 1.5, 1])
    
    with col1:
        d = st.date_input("생년월일 (양력)", key="input_date",
                          min_value=datetime(1900,1,1), max_value=datetime.now())
        gender = st.radio("성별", ("남성", "여성"), horizontal=True, key="input_gender")

    with col2:
        t = st.time_input("태어난 시간", key="input_time")
        st.caption("※ 시간 모르면 12:00 (오오) 설정")
        
    with col3:
        st.write("💾 **현재 정보 저장**")
        save_name = st.text_input("이름/별칭 입력", placeholder="예: 홍길동")
        if st.button("저장하기"):
            if save_name:
                save_user_profile(save_name, d, t, gender)
                st.rerun()
            else:
                st.warning("이름을 입력하세요.")

if st.button("전문가 분석 보기", type="primary", use_container_width=True):
    saju = get_saju_palja(d.year, d.month, d.day, t.hour, t.minute)
    
    calendar = KoreanLunarCalendar()
    calendar.setSolarDate(d.year, d.month, d.day)
    lunar_date = f"{calendar.lunarYear}년 {calendar.lunarMonth}월 {calendar.lunarDay}일"
    
    st.write("---")
    st.subheader(f"📅 {save_name if save_name else '분석 대상'} | 양력 {d.year}.{d.month}.{d.day} ({gender})")
    st.caption(f"음력: {lunar_date} | {t.strftime('%H시 %M분')} 출생")

    day_gan = saju['day'][0]
    def analyze_pillar(pillar):
        gan, ji = pillar[0], pillar[1]
        ten_gan = get_ten_gods(day_gan, gan) if pillar != saju['day'] else "본원(나)"
        ten_ji = get_ten_gods(day_gan, ji)
        unseong = get_12_unseong(day_gan, ji)
        return gan, ji, ten_gan, ten_ji, unseong

    y_data = analyze_pillar(saju['year'])
    m_data = analyze_pillar(saju['month'])
    d_data = analyze_pillar(saju['day'])
    t_data = analyze_pillar(saju['time'])

    st.markdown("""
    <style>
    .pillar-box { text-align: center; border: 2px solid #eee; padding: 15px; border-radius: 12px; background-color: #f8f9fa; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .ganji { font-size: 32px; font-weight: bold; color: #333; margin: 10px 0; font-family: 'KoPub Batang', serif; }
    .ten-god { font-size: 15px; color: #666; font-weight: 500;}
    .unseong { font-size: 14px; color: #e91e63; font-weight: bold; margin-top: 8px; background-color: #fce4ec; padding: 2px 8px; border-radius: 10px; display: inline-block;}
    .luck-title { font-size: 18px; font-weight: bold; color: #3f51b5; margin-bottom: 5px; }
    .desc-text { font-size: 12px; color: #888; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    def draw_pillar(col, title, data, luck_desc):
        gan, ji, t_g, t_j, un = data
        with col:
            st.markdown(f"""
            <div class="pillar-box">
                <div class="luck-title">{title}</div>
                <div class="desc-text">{luck_desc}</div>
                <div class="ten-god">{t_g}</div>
                <div class="ganji">{gan}<br>{ji}</div>
                <div class="ten-god">{t_j}</div>
                <div class="unseong">{un}</div>
            </div>
            """, unsafe_allow_html=True)

    draw_pillar(c1, "년주", y_data, "조상/초년")
    draw_pillar(c2, "월주", m_data, "부모/청년")
    draw_pillar(c3, "일주", d_data, "배우자/중년")
    draw_pillar(c4, "시주", t_data, "자식/말년")
    
    st.write("---")

    conn = sqlite3.connect('saju_app.db')
    cur = conn.cursor()
    cur.execute("SELECT meaning FROM saju_data WHERE ganji = ?", (saju['day'],))
    db_result = cur.fetchone()
    conn.close()
    
    fortune_text = db_result[0] if db_result else "운세 데이터 없음"
    
    st.subheader(f"📜 {saju['day']} 일주 상세 해석")
    st.success(fortune_text)
    st.info(f"💡 십이운성 분석: 당신의 일주는 **'{d_data[4]}'**의 기운(에너지 세기)을 가지고 있습니다.")

    st.markdown("### 📊 오행 에너지 분포")
    full_str = "".join([saju['year'], saju['month'], saju['day'], saju['time']])
    scores = {'목':0,'화':0,'토':0,'금':0,'수':0}
    for char in full_str:
        elem = ALL_CHAR_MAP.get(char)
        if elem: scores[elem] += 1
            
    df = pd.DataFrame({
        '오행': ['목 (나무)', '화 (불)', '토 (흙)', '금 (쇠)', '수 (물)'],
        '개수': [scores['목'], scores['화'], scores['토'], scores['금'], scores['수']],
        '색상': ['#4CAF50', '#FF5252', '#FBC02D', '#9E9E9E', '#3F51B5']
    })
    
    c = alt.Chart(df).mark_bar().encode(
        x=alt.X('개수', title='개수', axis=alt.Axis(tickMinStep=1)), 
        y=alt.Y('오행', sort=None),
        color=alt.Color('색상', scale=None, legend=None),
        tooltip=['오행', '개수']
    ).properties(height=250)
    
    text = c.mark_text(dx=10).encode(text='개수')
    st.altair_chart(c + text, use_container_width=True)