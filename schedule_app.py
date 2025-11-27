import re

import streamlit as st

st.set_page_config(page_title="스케줄 자동 생성기", layout="wide")

st.title("스케줄 자동 생성기")
st.caption("입력에 맞춰 가능한 한 균형 있게 주간 스케줄을 채워줘요.")

# 요일 순서: 월 ~ 일
DAYS = ["월", "화", "수", "목", "금", "토", "일"]

st.markdown(
    """
### 1) 요일별 필요 인원
"""
)

with st.expander("요일별 필요 인원 설정", expanded=True):
    cols = st.columns(7)
    required = {}
    for i, day in enumerate(DAYS):
        required[day] = cols[i].number_input(
            f"{day}", min_value=0, max_value=6, value=3, key=f"req_{day}"
        )

st.markdown(
    """
### 2) 출근 불가 요일 입력
"""
)

example = ""

raw = st.text_area("", value=example, height=220)


# 파싱: 오른쪽에 적힌 요일들은 "출근 불가"로 해석
def parse_input(text):
    employees_blocked = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if "-" not in ln:
            st.warning(f"")
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
if employees_available:
    with st.container(border=True):
        for name, avail in employees_available.items():
            st.write(
                f"- {name}: 가능한 요일 → {', '.join(avail) if avail else '없음(전부 불가)'}"
            )
else:
    st.info("직원 정보를 입력하면 여기에서 확인할 수 있어요.")

# 스케줄 생성 로직
MIN_TARGET = 3
SECONDARY_TARGET = 2
MAX_DAYS = 4


def attempt_schedule(employees_available, required, min_days):
    """그리디하게 스케줄을 생성하고, 모든 직원이 min_days 이상 채웠는지 반환."""

    schedule = {d: [] for d in DAYS}
    remaining = required.copy()
    assigned_count = {e: 0 for e in employees_available}

    employees_sorted = sorted(
        employees_available.keys(), key=lambda e: len(employees_available[e])
    )

    # 1) 최소 일수 우선 배정 (남은 필요 인원이 많은 요일을 먼저 소진)
    for e in employees_sorted:
        prefer_days = sorted(
            [d for d in DAYS if d in employees_available[e]],
            key=lambda d: remaining[d],
            reverse=True,
        )
        for day in prefer_days:
            if assigned_count[e] >= min_days:
                break
            if remaining[day] > 0:
                schedule[day].append(e)
                assigned_count[e] += 1
                remaining[day] -= 1

    # 2) 남은 자리 채우기 (근무 적은 직원 우선)
    for day in DAYS:
        while remaining[day] > 0:
            candidates = [
                e
                for e in employees_available
                if day in employees_available[e]
                and assigned_count[e] < MAX_DAYS
                and e not in schedule[day]
            ]
            if not candidates:
                break
            candidates.sort(key=lambda x: assigned_count[x])
            pick = candidates[0]
            schedule[day].append(pick)
            assigned_count[pick] += 1
            remaining[day] -= 1

    success = all(assigned_count[e] >= min_days for e in employees_available)
    return schedule, assigned_count, success


def generate_schedule(employees_available, required):
    # 1차: 전원 3일 이상 목표
    schedule, assigned_count, success = attempt_schedule(
        employees_available, required, MIN_TARGET
    )

    if not success:
        # 2차: 전원 2일 이상 목표로 재시도
        schedule, assigned_count, _ = attempt_schedule(
            employees_available, required, SECONDARY_TARGET
        )

    unmet = [d for d in DAYS if len(schedule[d]) < required[d]]
    return schedule, assigned_count, unmet, success


if st.button("스케줄 생성", type="primary"):
    if not employees_available:
        st.error("직원 정보가 없습니다. 입력을 확인하세요.")
    else:
        schedule, assigned_count, unmet, min3_success = generate_schedule(
            employees_available, required
        )

        st.subheader("생성된 스케줄")
        output_lines = []

        for day in DAYS:
            names = " ".join(schedule[day]) if schedule[day] else "휴무/없음"
            line = f"{day} {names}"
            output_lines.append(line)
            st.write(line)

        copy_text = "\n".join(output_lines)

        st.subheader("📋 복사하기")
        st.text_area("Copy Area", copy_text, height=200, key="copy_area")

        copy_js = """
<script>
function copyToClipboard() {
    const textarea = document.getElementById("copy_area");
    if (!textarea) {
        alert("textarea를 찾을 수 없습니다!");
        return;
    }
    navigator.clipboard.writeText(textarea.value)
        .then(() => {
            alert("복사 완료!");
        })
        .catch(err => {
            alert("복사 실패: " + err);
        });
}
</script>

<button onclick="copyToClipboard()" style="
    padding: 8px 16px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
">📄 복사하기</button>
"""
        st.markdown(copy_js, unsafe_allow_html=True)

        st.subheader("직원별 배정 일수")
        col1, col2 = st.columns(2)
        with col1:
            for e, cnt in assigned_count.items():
                st.write(f"- {e}: {cnt}일")
        with col2:
            if min3_success:
                st.success("모든 인원이 주 3일 이상 근무하도록 배치되었습니다.")
            else:
                st.info("3일 배치는 불가능하여, 최소 2일 이상으로 맞췄어요.")

        if unmet:
            for d in unmet:
                st.error(
                    f"{d}요일: 필요한 인원({required[d]})을 채우지 못했습니다. (배정: {len(schedule[d])})"
                )
        else:
            st.success("모든 요일의 필요 인원이 충족되었습니다.")
