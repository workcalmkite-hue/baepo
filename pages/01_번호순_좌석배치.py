import streamlit as st
import pandas as pd
import io
import os

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# =========================================================
# 0. PDF용 폰트 설정 (MaruBuri)
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    os.path.join(BASE_DIR, "fonts", "MaruBuri-Regular.ttf"),
    os.path.join(BASE_DIR, "..", "fonts", "MaruBuri-Regular.ttf"),
    os.path.join(BASE_DIR, "..", "fonts", "MaruBuri-Regular.otf"),
    os.path.join(BASE_DIR, "MaruBuri-Regular.ttf"),
]

FONT_PATH = None
for p in FONT_CANDIDATES:
    if os.path.exists(p):
        FONT_PATH = p
        break

KOREAN_FONT = "MaruBuri"
if FONT_PATH:
    try:
        pdfmetrics.registerFont(TTFont(KOREAN_FONT, FONT_PATH))
    except Exception:
        KOREAN_FONT = "Helvetica"
else:
    KOREAN_FONT = "Helvetica"


# =========================================================
# 1. 학생 dict → 좌석 표시용 dict
# =========================================================
def student_row_to_seat(row: pd.Series):
    if row is None:
        return None

    gender = str(row.get("성별", "")).strip()

    if gender in ["F", "여", "여자", "f", "female", "FEMALE"]:
        color = "#F5B7B1"  # 여학생
    elif gender in ["M", "남", "남자", "m", "male", "MALE"]:
        color = "#A9CCE3"  # 남학생
    else:
        color = "#e5e7eb"  # 기타/미지정

    num_str = str(row.get("출석 번호", "")).strip()
    name_str = str(row.get("이름", "")).strip()
    label = f"{num_str} {name_str}".strip()

    return {"name": label, "color": color}


# =========================================================
# 2. 번호순 좌석 배치 로직
# =========================================================
def assign_seats_by_number(
    df: pd.DataFrame, rows: int, bun_dan: int, sort_order: str, start_side: str
):
    # sort_order: "asc" or "desc"
    # start_side: "left" or "right"
    df_sorted = df.copy()

    df_sorted["__번호_sort__"] = pd.to_numeric(df_sorted["출석 번호"], errors="coerce")
    df_sorted = df_sorted.sort_values(
        "__번호_sort__", ascending=(sort_order == "asc")
    ).reset_index(drop=True)

    cols = bun_dan
    total_seats = rows * cols

    if len(df_sorted) > total_seats:
        df_sorted = df_sorted.iloc[:total_seats]

    seat_matrix = [[None for _ in range(cols)] for _ in range(rows)]

    idx = 0
    for r in range(rows):  # r=0 이 앞줄
        if start_side == "left":
            col_range = range(cols)  # 왼쪽 -> 오른쪽
        else:
            col_range = range(cols - 1, -1, -1)  # 오른쪽 -> 왼쪽

        for c in col_range:
            if idx < len(df_sorted):
                seat_matrix[r][c] = student_row_to_seat(df_sorted.iloc[idx])
                idx += 1
            else:
                break

    return seat_matrix


# =========================================================
# 3. 화면용 HTML 렌더링
# =========================================================
HTML_STYLE = """
<style>
    .desk-grid {
        display: grid;
        gap: 10px;
        padding: 20px;
        background-color: #f4f4f9;
        border-radius: 12px;
        width: fit-content;
    }
    .desk {
        width: 120px;
        height: 58px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 15px;
        padding: 4px;
        border: 2px solid #555;
    }
    .empty-desk {
        background-color: #e0e7ff;
        border-style: dashed;
        color: #9ca3af;
    }
    .front-of-class {
        font-size: 1.6em;
        font-weight: 900;
        color: #2563eb;
        border: 3px solid #2563eb;
        padding: 8px 16px;
        border-radius: 12px;
        background-color: #eff6ff;
        display: inline-block;
    }
</style>
"""


def render_chart(matrix):
    cols = len(matrix[0])
    html = f'<div class="desk-grid" style="grid-template-columns: repeat({cols}, auto);">'

    for row in matrix:
        for desk in row:
            classes = "desk"
            if desk:
                style = f"background-color:{desk['color']};border-color:{desk['color']};"
                name = desk["name"]
            else:
                classes += " empty-desk"
                style = ""
                name = "빈 자리"

            html += f'<div class="{classes}" style="{style}">{name}</div>'

    html += "</div>"
    return html


# =========================================================
# 4. PDF 생성 함수들 (Single 모드만 사용)
# =========================================================
def draw_pdf_page(c, matrix, view_mode, title):
    width, height = landscape(A4)

    margin_y = 80
    gap_x = 10
    gap_y = 18

    # 1) 행 순서
    if view_mode == "teacher":
        matrix_to_draw = matrix[::-1]   # 교사용: 앞줄이 아래
    else:
        matrix_to_draw = matrix         # 학생용: 앞줄이 위

    rows = len(matrix_to_draw)
    cols = len(matrix_to_draw[0])

    # 2) 제목 위치
    if view_mode == "teacher":
        title_y = height - 40
    else:
        title_y = margin_y / 2

    c.setFont(KOREAN_FONT, 26)
    c.drawCentredString(width / 2, title_y, title)

    # 3) 좌석 영역 계산 (짝 모드 아님)
    available_h = height - margin_y * 2 - 80
    cell_h = (available_h - gap_y * (rows - 1)) / rows if rows > 0 else 40

    total_base_gaps = (cols - 1) * gap_x
    available_w = width - 80
    cell_w = (available_w - total_base_gaps) / cols if cols > 0 else 40

    total_width = cols * cell_w + total_base_gaps
    start_x = (width - total_width) / 2

    # 4) 세로 시작점
    if view_mode == "teacher":
        start_y = height - margin_y - cell_h
    else:
        start_y = height - margin_y - cell_h - 60  # 학생용: 조금 더 아래

    # 5) 좌석 그리기
    for r, row in enumerate(matrix_to_draw):
        y = start_y - r * (cell_h + gap_y)
        x = start_x

        for desk in row:
            if desk:
                c.setFillColor(HexColor(desk["color"]))
                c.setStrokeColor(HexColor(desk["color"]))
            else:
                c.setFillColor(HexColor("#e0e7ff"))
                c.setStrokeColor(HexColor("#d1d5db"))

            c.rect(x, y, cell_w, cell_h, fill=1, stroke=1)

            c.setFillColor(black)
            if desk:
                c.setFont(KOREAN_FONT, 16)
                c.drawCentredString(x + cell_w / 2, y + cell_h / 2 - 5, desk["name"])
            else:
                c.setFont(KOREAN_FONT, 14)
                c.drawCentredString(x + cell_w / 2, y + cell_h / 2 - 5, "빈 자리")

            x += cell_w + gap_x

    # 6) 교탁
    desk_w = 130
    desk_h = 48
    desk_x = width / 2 - desk_w / 2

    if view_mode == "teacher":
        desk_y = margin_y - desk_h
    else:
        desk_y = start_y + cell_h + 20

    c.setFillColor(HexColor("#eff6ff"))
    c.setStrokeColor(HexColor("#2563eb"))
    c.rect(desk_x, desk_y, desk_w, desk_h, fill=1, stroke=1)
    c.setFont(KOREAN_FONT, 18)
    c.setFillColor(HexColor("#2563eb"))
    c.drawCentredString(desk_x + desk_w / 2, desk_y + desk_h / 2 - 4, "교탁")


def make_pdf(matrix, view_mode, title):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    draw_pdf_page(c, matrix, view_mode, title)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def make_pdf_both(matrix):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    draw_pdf_page(c, matrix, "teacher", "교사용 번호순 좌석 배치표")
    c.showPage()
    draw_pdf_page(c, matrix, "student", "학생용 번호순 좌석 배치표")
    c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()


# =========================================================
# 5. Streamlit UI
# =========================================================
st.set_page_config(page_title="번호순 좌석 배치", layout="centered")
st.markdown(HTML_STYLE, unsafe_allow_html=True)

st.title("📝 번호순 좌석 배치표 (시험용)")

st.markdown(
    """
### 1️⃣ 엑셀 업로드

엑셀 파일 형식은 다음과 같이 준비해 주세요.

- **1열: 출석 번호**  
- **2열: 이름**  
- **3열: 성별**  

첫 행은 반드시 **헤더(열 이름)** 로 입력해 주세요.  
예시: `출석 번호 | 이름 | 성별`
"""
)

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)

        required_cols = ["출석 번호", "이름", "성별"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"❌ 엑셀에 {required_cols} 컬럼이 모두 있어야 합니다.")
        else:
            st.success("✅ 엑셀을 성공적으로 불러왔습니다.")
            with st.expander("불러온 학생 명단 보기"):
                st.dataframe(df)

            st.markdown("---")
            st.subheader("2️⃣ 배치 옵션 선택")

            col1, col2, col3 = st.columns(3)
            with col1:
                sort_option = st.selectbox(
                    "정렬 기준",
                    ["번호 낮은순 → 높은순", "번호 높은순 → 낮은순"],
                )
                sort_order = "asc" if "낮은순" in sort_option else "desc"
            with col2:
                start_side_option = st.selectbox(
                    "시작 위치",
                    ["왼쪽 앞에서부터", "오른쪽 앞에서부터"],
                )
                start_side = "left" if "왼쪽" in start_side_option else "right"
            with col3:
                bun_dan = st.number_input("분단 수", min_value=2, max_value=10, value=4)
            rows = st.number_input("줄 수(행)", min_value=2, max_value=10, value=6)

            if st.button("📚 번호순 좌석 배치 생성", type="primary"):
                cols = int(bun_dan)
                total_seats = int(rows) * cols
                num_students = len(df)

                if total_seats < num_students:
                    st.error("⚠️ 좌석이 부족해요!")
                    st.warning(f"학생 {num_students}명 / 자리 {total_seats}석")
                else:
                    matrix = assign_seats_by_number(
                        df, int(rows), int(bun_dan), sort_order, start_side
                    )

                    st.markdown("---")
                    st.subheader("3️⃣ 번호순 좌석 배치 결과 (화면용)")

                    st.markdown(
                        '<div style="text-align:center;"><span class="front-of-class">교탁</span></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(render_chart(matrix), unsafe_allow_html=True)

                    # PDF 생성
                    teacher_pdf = make_pdf(
                        matrix, "teacher", "교사용 번호순 좌석 배치표"
                    )
                    student_pdf = make_pdf(
                        matrix, "student", "학생용 번호순 좌석 배치표"
                    )
                    both_pdf = make_pdf_both(matrix)

                    st.markdown("---")
                    st.subheader("4️⃣ PDF 다운로드")

                    d1, d2, d3 = st.columns(3)
                    with d1:
                        st.download_button(
                            "📥 교사용 PDF",
                            teacher_pdf,
                            file_name="number_seating_teacher.pdf",
                            mime="application/pdf",
                        )
                    with d2:
                        st.download_button(
                            "📥 학생용 PDF",
                            student_pdf,
                            file_name="number_seating_student.pdf",
                            mime="application/pdf",
                        )
                    with d3:
                        st.download_button(
                            "📥 교사+학생 한 번에",
                            both_pdf,
                            file_name="number_seating_both.pdf",
                            mime="application/pdf",
                        )

    except Exception as e:
        st.error(f"엑셀을 읽는 중 오류가 발생했습니다: {e}")
else:
    st.info("엑셀 파일을 업로드하면 번호순 좌석 배치를 시작할 수 있습니다 😊")
