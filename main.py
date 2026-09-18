import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2 - 분포와 관계", layout="wide"
)

# 제목
st.title("영화 데이터 그래프 도감 2 - 분포와 관계")


# 데이터 불러오기 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"
    df = pd.read_csv(url)

    # 장르 전처리: 세로막대 기호(|)로 분리 후 첫 번째 장르만 추출
    df["genre"] = df["genre"].astype(str).apply(lambda x: x.split("|")[0])

    return df


df = load_data()

# --- 첫 번째 그래프: 장르별 영화 편수 (도넛 그래프) ---
st.subheader("1. 장르별 영화 편수 분포")

# 장르별 편수 집계
genre_counts = df["genre"].value_counts().reset_index()
genre_counts.columns = ["장르", "편수"]

# Plotly 도넛 그래프 생성
fig1 = px.pie(
    genre_counts,
    values="편수",
    names="장르",
    hole=0.4,
    title="장르별 영화 편수 및 비율",
)

# 마우스 오버 시 편수와 비율이 함께 표시되도록 설정
fig1.update_traces(hovertemplate="<b>%{label}</b><br>편수: %{value}편<br>비율: %{percent}")

st.plotly_chart(fig1, use_container_width=True)

# 첫 번째 그래프 설명 구역
st.info(
    "**이 그래프로 알 수 있는 것:** 특정 장르가 전체 개봉작 중 얼마나 큰 비중을 차지하는지 한눈에 파악할 수 있습니다."
)

st.divider()

# --- 두 번째 그래프: 장르 및 영화별 총 관객 수 (트리맵) ---
st.subheader("2. 장르 및 영화별 총 관객 수")

# Plotly 트리맵 생성 (장르 > 영화명 계층 구조, 칸 크기는 총 관객 수)
fig2 = px.treemap(
    df,
    path=["genre", "movieNm"],
    values="total_audi",
    title="장르 및 개별 영화별 총 관객 수 트리맵",
)

# 마우스 오버 시 영화명(또는 장르)과 총 관객 수가 명확하게 보이도록 설정
fig2.update_traces(
    hovertemplate="<b>%{label}</b><br>총 관객 수: %{value:,}명<extra></extra>"
)

st.plotly_chart(fig2, use_container_width=True)

# 두 번째 그래프 설명 구역
st.info(
    "**이 그래프로 알 수 있는 것:** 장르 전체의 규모뿐만 아니라 그 안에서 어떤 영화가 흥행을 주도했는지 직관적으로 비교할 수 있습니다."
)
