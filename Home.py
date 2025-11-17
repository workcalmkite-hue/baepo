import streamlit as st

st.set_page_config(page_title="좌석 배치 사이트", layout="centered")

st.title("🧑‍🏫 좌석 배치 사이트")

st.markdown(
    """
이 사이트는 **엑셀 파일을 업로드**해서

1. 랜덤 좌석 배치표 만들기  
2. 번호순(시험용) 좌석 배치표 만들기  

를 할 수 있는 멀티 페이지 앱입니다.

왼쪽 상단의 **Pages / 페이지 메뉴**에서  
원하는 기능을 선택해 주세요.
"""
)

