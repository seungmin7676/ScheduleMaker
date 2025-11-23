# schedule_app.py (수정판)
import streamlit as st
import re
from collections import defaultdict

st.set_page_config(page_title="스케줄 자동 생성기", layout="wide")
st.title("스케줄 자동 생성기")

# 요일 순서: 월 ~ 일
DAYS = ["월", "화", "수", "목", "금", "토", "일"]

st.header("요일별 필요 인원 설정")
required = {}
for day in DAYS:
    required[day] = st.number_input(f"{day}요일 출근 인원", min_value=0, max_value=6, value=3, key=f"req_{day}")


st.header("출근 불가 요일 입력")
example = ""
raw = st.text_area("", value=example, height=200)

# 파싱: 오른쪽에 적힌 요일들은 "출근 불가"로 해석
def parse_input(text):
    employees_blocked = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if "-" not in ln:
            st.warning(f"무시되는 라인(형식오류): {ln}")
            continue
        name, right = ln.split("-", 1)
        name = name.strip()
        right = right.strip()
        # x 또는 빈칸 => 제한 없음 (blocked = [])
        if right == "" or right.lower() == "x":
            blocked = []
        else:
            blocked = re.findall(r"(월|화|수|목|금|토|일)", right)
        employees_blocked[name] = blocked
    return employees_blocked

employees_blocked = parse_input(raw)

# 사용자가 보기 좋게, 각 직원의 실제 "가능한 요일"을 계산
employees_available = {}
for name, blocked in employees_blocked.items():
    employees_available[name] = [d for d in DAYS if d not in blocked]

st.subheader("가능한 요일")
for name, avail in employees_available.items():
    st.write(f"- {name}: 가능한 요일 → {', '.join(avail) if avail else '없음(전부 불가)'}")

# 스케줄 생성 로직
MIN_DAYS = 3
MAX_DAYS = 4

def generate_schedule(employees_available, required):
    # 초기화
    schedule = {d: [] for d in DAYS}
    remaining = required.copy()
    assigned_count = {e: 0 for e in employees_available}

    # 직원별 가용일 수가 적은 사람부터 처리 (harder first)
    employees_sorted = sorted(employees_available.keys(), key=lambda e: len(employees_available[e]))

    # 1) 가능한 경우: **각 직원이 최소 MIN_DAYS** 가 되도록 시도
    # 직원별로 가능한 날 중에서 아직 필요 인원이 남아있는 날에 배치 (앞에서부터)
    for e in employees_sorted:
        for day in DAYS:
            if assigned_count[e] >= MIN_DAYS:
                break
            if day in employees_available[e] and remaining[day] > 0:
                schedule[day].append(e)
                assigned_count[e] += 1
                remaining[day] -= 1

    # 2) MIN 보장 후, 남은 자리를 채우되 **근무가 적은 직원 우선**, 최대 MAX_DAYS 까지
    # 반복: 각 요일에 대해 아직 남은 자리 있으면 가능한 직원 리스트에서 할당
    # 직원 선택 우선순위: assigned_count 적은 순, 그리고 그날 가능해야 함, 그리고 < MAX_DAYS
    for day in DAYS:
        while remaining[day] > 0:
            # 후보: 가능한 직원 중 아직 MAX_DAYS 미만이고 그날 가능한 사람
            candidates = [e for e in employees_available if day in employees_available[e] and assigned_count[e] < MAX_DAYS and e not in schedule[day]]
            if not candidates:
                # 더 이상 배치 불가
                break
            # 선택: 근무가 적은 사람 우선 (균형 맞추기)
            candidates.sort(key=lambda x: assigned_count[x])
            pick = candidates[0]
            schedule[day].append(pick)
            assigned_count[pick] += 1
            remaining[day] -= 1

    # 3) 조건 충족 검사: 모든 직원이 MIN_DAYS 이상인지 확인
    all_min_ok = all(assigned_count[e] >= MIN_DAYS for e in employees_available)

    # 4) 만약 MIN 조건을 모두 만족하지 못하면 **fallback**: MIN 조건 무시하고 단순 그리디 배치(최소한 required 채우기)
    if not all_min_ok:
        # 재초기화
        schedule = {d: [] for d in DAYS}
        remaining = required.copy()
        assigned_count = {e: 0 for e in employees_available}

        # 간단한 그리디: 요일 순서대로, 가능한 직원 중 근무 적은 사람 우선 배정(<=MAX_DAYS)
        for day in DAYS:
            while remaining[day] > 0:
                candidates = [e for e in employees_available if day in employees_available[e] and assigned_count[e] < MAX_DAYS and e not in schedule[day]]
                if not candidates:
                    break
                candidates.sort(key=lambda x: assigned_count[x])
                pick = candidates[0]
                schedule[day].append(pick)
                assigned_count[pick] += 1
                remaining[day] -= 1

    # 최종: 반환 (schedule, assigned_count, 부족한 요일 리스트)
    unmet = [d for d in DAYS if len(schedule[d]) < required[d]]
    return schedule, assigned_count, unmet

if st.button("스케줄 생성"):
    if not employees_available:
        st.error("직원 정보가 없습니다. 입력을 확인하세요.")
    else:
        schedule, assigned_count, unmet = generate_schedule(employees_available, required)

        # 스케줄 출력
        st.subheader("생성된 스케줄")
        output_lines = []
        
        for day in DAYS:
            names = " ".join(schedule[day]) if schedule[day] else "휴무/없음"
            line = f"{day} {names}"
            output_lines.append(line)
            st.write(line)
        
        # 복사용 텍스트 생성
        copy_text = "\n".join(output_lines)
        
        st.text_area("", copy_text, height=200, key="copy_area")
        
        copy_js = """
        <script>
        function copyText() {
            const textarea = document.querySelector('textarea[key="copy_area"]');
            navigator.clipboard.writeText(textarea.value)
                .then(() => alert("복사 완료!"))
                .catch(err => alert("복사 실패: " + err));
        }
        </script>
        <button onclick="copyText()" style="
            padding: 8px 16px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            border-radius: 6px;
        ">📄 복사하기</button>
        """
        st.markdown(copy_js, unsafe_allow_html=True)
        st.subheader("직원별 배정 일수")
        for e, cnt in assigned_count.items():
            st.write(f"- {e}: {cnt}일")

        if unmet:
            for d in unmet:
                st.error(f"{d}요일: 필요한 인원({required[d]})을 채우지 못했습니다. (배정: {len(schedule[d])})")
        else:
            st.success("모든 요일의 필요 인원이 충족되었습니다.")
