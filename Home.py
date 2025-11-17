import streamlit as st

st.set_page_config(page_title="좌석 배치 도구", layout="centered")

st.title("🧑‍🏫 좌석 배치 도구")

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

st.markdown("---")

st.markdown(
    """
**사용 방법 요약**

- 엑셀 파일 형식  
  - 1열: `출석 번호`  
  - 2열: `이름`  
  - 3열: `성별` (예: M / F 또는 남 / 여)

각 페이지에서 엑셀을 업로드한 뒤  
좌석 형태, 분단 수, 줄 수(행)를 설정하면  
즉시 좌석 배치 결과와 PDF를 받을 수 있습니다.
"""
)

st.markdown("---")

st.markdown(
    """
**출처 / 제작자**

- 방배중학교 기술 교사 **안정연**  
- 문의 이메일: [jooyeon0714@naver.com](mailto:jooyeon0714@naver.com)
"""
)
