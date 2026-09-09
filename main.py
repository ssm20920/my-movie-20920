import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 기본 설정 (제목, 레이아웃 등)
st.set_page_config(
    page_title="어제 박스오피스 순위",
    page_icon="🎬",
    layout="wide"
)

# 2. 한국 시간(KST) 기준으로 '어제' 날짜 구하기
# 배포 서버의 시계가 해외 기준일 수 있으므로 Asia/Seoul 타임존을 지정합니다.
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.now(kst)
yesterday_kst = now_kst - timedelta(days=1)
target_dt = yesterday_kst.strftime("%Y%m%d") # API용 날짜 형식 (YYYYMMDD)
display_date = yesterday_kst.strftime("%Y년 %m월 %d일") # 화면 표시용 날짜 형식

st.title("🎬 일별 박스오피스 순위")
st.caption(f"기준일: {display_date} (한국 시간 기준 어제)")

# 3. KOBIS API 데이터 불러오기 함수 (캐싱 적용)
# @st.cache_data를 사용하여 1시간(3600초) 동안 동일 날짜 요청 시 API를 다시 호출하지 않고 저장된 결과를 사용합니다.
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": date_str
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # HTTP 요청 자체가 실패한 경우
        if response.status_code != 200:
            return None, f"서버 통신 실패 (상태 코드: {response.status_code})"
            
        data = response.json()
        
        # 인증키 오류 등으로 인한 faultInfo 반환 확인
        if "faultInfo" in data:
            fault_msg = data["faultInfo"].get("message", "알 수 없는 오류가 발생했습니다.")
            return None, f"KOBIS API 오류: {fault_msg}"
            
        # 정상 응답 구조 확인
        box_office_result = data.get("boxOfficeResult", {})
        movie_list = box_office_result.get("dailyBoxOfficeList", [])
        
        # 영화 목록이 비어있는 경우
        if not movie_list:
            return None, "해당 날짜의 박스오피스 데이터가 존재하지 않거나 집계 중입니다."
            
        return movie_list, None

    except requests.exceptions.RequestException as e:
        return None, f"네트워크 요청 중 에러 발생: {str(e)}"

# 4. Streamlit Secrets(비밀 금고)에서 인증키 불러오기 및 예외 처리
if "KOBIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `KOBIS_KEY`가 설정되어 있지 않습니다.")
    st.info("💡 **확인 방법:** Streamlit Cloud 설정(App settings -> Secrets)에 `KOBIS_KEY = '발급받은키'` 형식으로 작성되어 있는지 확인하세요.")
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# 5. 데이터 가져오기 실행 및 에러 처리
raw_data, error_message = fetch_box_office_data(api_key, target_dt)

if error_message:
    st.error(f"❌ 데이터를 가져오지 못했습니다: {error_message}")
    st.warning("💡 **확인해 보세요:**\n1. `KOBIS_KEY`가 올바른 발급 키인지 확인하세요.\n2. KOBIS 홈페이지의 API 일일 사용량을 초과했는지 확인하세요.")
    st.stop()

# 6. 데이터 전처리 (문자열 -> 숫자 변환)
df = pd.DataFrame(raw_data)

# 숫자형 변환을 적용할 컬럼들
numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# 순위 기준 정렬
df = df.sort_values("rank").reset_index(drop=True)

# 7. 1위 영화 지표 카드 (st.metric) 표시
top_1 = df.iloc[0]

st.subheader(f"🥇 1위: {top_1['movieNm']}")

col1, col2, col3 = st.columns(3)
col1.metric(
    label="일별 관객수", 
    value=f"{top_1['audiCnt']:,} 명", 
    delta=f"전날 대비 순위 {top_1['rankInten']}"
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

# 8. 관객수 상위 5편 막대그래프 표시
st.subheader("📊 관객수 상위 5개 영화")
top_5_df = df.head(5)

# 그래프용 데이터 가공 (영화명을 인덱스로 지정하여 그래프 축 레이블로 활용)
chart_data = top_5_df.set_index("movieNm")[["audiCnt"]]
chart_data.columns = ["일별 관객수"]

st.bar_chart(chart_data)

st.divider()

# 9. 관객수 상위 5편 막대그래프 표시 (오름차순 정렬)
st.subheader("📊 관객수 상위 5개 영화")

# 관객수(audiCnt) 기준 오름차순 정렬 후 상위 5개 추출
top_5_df = df.sort_values("audiCnt", ascending=True).tail(5)

# 그래프용 데이터 가공 (영화명을 인덱스로 지정)
chart_data = top_5_df.set_index("movieNm")[["audiCnt"]]
chart_data.columns = ["일별 관객수"]

st.bar_chart(chart_data)
    }
)
import datetime
import pandas as pd
import requests
import streamlit as st

KST = datetime.timezone(datetime.timedelta(hours=9))
어제 = datetime.datetime.now(KST).date() - datetime.timedelta(days=1)
고른날 = st.date_input("날짜를 고르세요", value=어제, max_value=어제)

URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"


@st.cache_data(ttl=3600)
def fetch(day_text):
    res = requests.get(URL, params={"key": st.secrets["KOBIS_KEY"], "targetDt": day_text}, timeout=20)
    answer = res.json().get("boxOfficeResult")
    return answer["dailyBoxOfficeList"] if answer else []


movies = fetch(고른날.strftime("%Y%m%d"))
if not movies:
    st.info("그날은 아직 집계 전입니다.")
    st.stop()

표 = pd.DataFrame([{
    "순위": int(m["rank"]),
    "영화명": ("🏆 " if int(m["audiAcc"]) >= 1_000_000 else "") + m["movieNm"],
    "순위 변화": ("🔺" + str(int(m["rankInten"])) if int(m["rankInten"]) > 0
                 else "🔻" + str(-int(m["rankInten"])) if int(m["rankInten"]) < 0 else "—"),
    "관객수": int(m["audiCnt"]),
    "누적관객": int(m["audiAcc"]),
} for m in movies])
st.dataframe(표, hide_index=True)
st.caption("🔺 오른 영화 · 🔻 내린 영화 · 🏆 누적 100만 명을 넘은 영화")




        
  
