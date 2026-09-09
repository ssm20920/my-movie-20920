import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 기본 설정 (제목, 레이아웃 등)
st.set_page_config(
    page_title="일별 박스오피스 검색",
    page_icon="🎬",
    layout="wide"
)

# 2. 한국 시간(KST) 기준 '어제' 날짜 구하기 (달력 최대 선택일)
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.now(kst)
yesterday_kst = (now_kst - timedelta(days=1)).date()

st.title("🎬 일별 박스오피스 순위")

# 3. 사이드바 - 날짜 선택 달력 기능 (최대 선택 날짜는 어제까지)
st.sidebar.header("🗓️ 날짜 선택")
selected_date = st.sidebar.date_input(
    label="조회할 날짜를 선택하세요",
    value=yesterday_kst,
    max_value=yesterday_kst
)

# API 요청을 위한 날짜 형식 변환 (YYYYMMDD) 및 화면 표시용 형식
target_dt = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

st.caption(f"기준일: {display_date}")

# 4. KOBIS API 데이터 불러오기 함수 (1시간 캐싱 적용)
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": date_str
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None, f"서버 통신 실패 (상태 코드: {response.status_code})"
            
        data = response.json()
        
        # faultInfo 오류 체크
        if "faultInfo" in data:
            fault_msg = data["faultInfo"].get("message", "알 수 없는 오류가 발생했습니다.")
            return None, f"KOBIS API 오류: {fault_msg}"
            
        box_office_result = data.get("boxOfficeResult", {})
        movie_list = box_office_result.get("dailyBoxOfficeList", [])
        
        # 영화 목록이 비어있는 경우
        if not movie_list:
            return None, "그날은 아직 집계 전입니다"
            
        return movie_list, None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 요청 중 에러 발생: {str(e)}"

# 5. Secrets 키 검증 및 불러오기
if "KOBIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `KOBIS_KEY`가 설정되어 있지 않습니다.")
    st.info("💡 **확인 방법:** Streamlit Cloud 설정(App settings -> Secrets)에 `KOBIS_KEY = '발급받은키'` 형식으로 작성되어 있는지 확인하세요.")
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# 6. 데이터 가져오기 실행
raw_data, error_message = fetch_box_office_data(api_key, target_dt)

if error_message:
    if error_message == "그날은 아직 집계 전입니다":
        st.info(f"ℹ️ {error_message}")
    else:
        st.error(f"❌ 데이터를 가져오지 못했습니다: {error_message}")
        st.warning("💡 **확인해 보세요:**\n1. `KOBIS_KEY`가 올바른 발급 키인지 확인하세요.\n2. KOBIS 홈페이지의 API 일일 사용량을 초과했는지 확인하세요.")
    st.stop()

# 7. 데이터 전처리
df = pd.DataFrame(raw_data)

# 숫자 데이터 형변환 (문자열 -> 숫자)
numeric_columns = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# 순위 정렬
df = df.sort_values("rank").reset_index(drop=True)

# 7-1. 순위 증감(rankInten) 텍스트 및 색상 변환 함수
def format_rank_change(change):
    if change > 0:
        return f"🔺 {change}"  # 오른 경우 (빨간 위 화살표)
    elif change < 0:
        return f"🔹 {abs(change)}"  # 내린 경우 (파란 아래 화살표)
    else:
        return "-"  # 변동 없음

df["rankChangeDisplay"] = df["rankInten"].apply(format_rank_change)

# 7-2. 누적관객 100만 명 이상 트로피 이모지 추가
df["movieNmDisplay"] = df.apply(
    lambda row: f"{row['movieNm']} 🏆" if row["audiAcc"] >= 1000000 else row["movieNm"],
    axis=1
)

# 8. 1위 영화 지표 카드 표시
top_1 = df.iloc[0]

st.subheader(f"🥇 1위: {top_1['movieNmDisplay']}")

col1, col2, col3 = st.columns(3)
col1.metric(
    label="일별 관객수", 
    value=f"{top_1['audiCnt']:,} 명", 
    delta=f"순위 변동 {top_1['rankChangeDisplay']}"
)
col2.metric(
    label="누적 관객수", 
    value=f"{top_1['audiAcc']:,} 명"
)
col3.metric(
    label="스크린수", 
    value=f"{top_1['scrnCnt']:,} 개"
)

st.divider()

# 9. 관객수 상위 5편 막대그래프 표시 (오름차순 정렬)
st.subheader("📊 관객수 상위 5개 영화")

# 관객수(audiCnt) 기준 오름차순 정렬 후 상위 5개 추출
top_5_df = df.sort_values("audiCnt", ascending=True).tail(5)

# 그래프용 데이터 가공 (영화명을 인덱스로 지정)
chart_data = top_5_df.set_index("movieNm")[["audiCnt"]]
chart_data.columns = ["일별 관객수"]

st.bar_chart(chart_data)

st.divider()

# 10. 전체 박스오피스 순위 표 (DataFrame) 출력
st.subheader("📋 전체 순위 목록")

display_df = df[["rank", "rankChangeDisplay", "movieNmDisplay", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(format="%d위"),
        "관객수": st.column_config.NumberColumn(format="%d명"),
        "누적관객": st.column_config.NumberColumn(format="%d명"),
        "스크린수": st.column_config.NumberColumn(format="%d개")
    }
)
