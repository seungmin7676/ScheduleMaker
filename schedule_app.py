import re
import streamlit as st

st.set_page_config(page_title="스케줄 자동 생성기", layout="wide")

st.title("화포식당 스케줄 자동 생성기")

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
`이름 - 불가능 요일` 형식으로 적어주세요. 요일이 없는 경우 `x`를 사용합니다.
"""
)

example = """"""
raw = st.text_area("", value=example, height=220)


def parse_input(text: str):
    """'이름 - 불가능 요일' 입력을 파싱해 직원별 불가 요일 리스트를 만든다."""
    employees_blocked = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if "-" not in ln:
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

# 직원별 가능한 요일
employees_available = {}
for name, blocked in employees_blocked.items():
    employees_available[name] = [d for d in DAYS if d not in blocked]

st.subheader("가능한 요일")
if employees_available:
    with st.container(border=True):
        for name, avail in employees_available.items():
            st.write(f"- {name}: 가능한 요일 → {', '.join(avail) if avail else '없음(전부 불가)'}")
else:
    st.info("직원 정보를 입력하면 여기에서 확인할 수 있어요.")

# 스케줄 생성 로직
MIN_TARGET = 3
SECONDARY_TARGET = 2
MAX_DAYS = 4


def attempt_schedule(employees_available, required, min_days):
    """
    그리디하게 스케줄을 생성하고,
    모든 직원이 min_days 이상 채웠는지(success) 반환.
    """
    schedule = {d: [] for d in DAYS}
    remaining = required.copy()
    assigned_count = {e: 0 for e in employees_available}

    # 가능한 요일이 적은 직원부터
    employees_sorted = sorted(employees_available.keys(), key=lambda e: len(employees_available[e]))

    # 1) 최소 일수 우선 배정
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
    schedule, assigned_count, success = attempt_schedule(employees_available, required, MIN_TARGET)

    if not success:
        # 2차: 전원 2일 이상 목표로 재시도
        schedule, assigned_count, _ = attempt_schedule(employees_available, required, SECONDARY_TARGET)

    unmet = [d for d in DAYS if len(schedule[d]) < required[d]]
    return schedule, assigned_count, unmet, success


def build_assigned_by_employee(schedule):
    """schedule(요일->직원들)로부터 직원별 배정 요일 리스트를 만든다."""
    assigned_by_employee = {e: [] for e in employees_available}
    for day in DAYS:
        for name in schedule[day]:
            if name in assigned_by_employee and day not in assigned_by_employee[name]:
                assigned_by_employee[name].append(day)
    return assigned_by_employee


if st.button("스케줄 생성", type="primary"):
    if not employees_available:
        st.error("직원 정보가 없습니다. 입력을 확인하세요.")
    else:
        schedule, assigned_count, unmet, min3_success = generate_schedule(employees_available, required)

        st.subheader("생성된 스케줄")
        output_lines = []
        for day in DAYS:
            names = " ".join(schedule[day]) if schedule[day] else "휴무/없음"
            output_lines.append(f"{day} {names}")

        copy_text = "\n".join(output_lines)
        st.text_area("Copy Area", copy_text, height=200, key="copy_area")

        # ✅ 직원별 배정 상세(요일 포함)
        assigned_by_employee = build_assigned_by_employee(schedule)

        st.subheader("직원별 배정 정보")

        st.markdown("**배정 상세**")
        for e in sorted(assigned_count.keys(), key=lambda x: assigned_count[x], reverse=True):
            days_list = assigned_by_employee.get(e, [])
            days_str = ", ".join(days_list) if days_list else "배정 없음"
            st.write(f"- {e}: {assigned_count[e]}일 / 배정 요일 → {days_str}")

        if min3_success:
            st.success("모든 인원이 주 3일 이상 근무하도록 배치되었습니다.")
        else:
            st.info("3일 배치는 불가능하여, 최소 2일 이상으로 맞췄어요.")

        if unmet:
            for d in unmet:
                st.error(f"{d}요일: 필요한 인원({required[d]})을 채우지 못했습니다. (배정: {len(schedule[d])})")

st.divider()

st.markdown(
    """
### 3) 직접 작성한 스케줄 검증
아래에 직접 만든 스케줄을 입력하면 **출근 불가 요일**과 **주 3일 이상 근무** 조건을 확인합니다.
"""
)

manual_example = """"""
manual_text = st.text_area(
    "직접 작성한 스케줄 입력",
    value=manual_example,
    height=200,
    help="각 줄에 '요일 이름1 이름2 ...' 형식으로 입력하세요.",
)


def parse_manual_schedule(text: str):
    schedule = {d: [] for d in DAYS}
    invalid_lines = []

    for ln in [line.strip() for line in text.splitlines() if line.strip()]:
        match = re.match(r"^(월|화|수|목|금|토|일)\s*(.*)$", ln)
        if not match:
            invalid_lines.append(ln)
            continue

        day, rest = match.groups()
        tokens = re.findall(r"[^\s,]+", rest)
        names = [t for t in tokens if t not in {"휴무/없음", "휴무", "없음", "-", "x", "X"}]
        schedule[day] = list(dict.fromkeys(names))  # 중복 제거(입력 순서 유지)

    return schedule, invalid_lines


if st.button("스케줄 검증"):
    if not employees_available:
        st.error("직원 정보가 없습니다. 출근 불가 요일을 입력해주세요.")
    else:
        manual_schedule, invalid_lines = parse_manual_schedule(manual_text)

        assigned_days = {e: 0 for e in employees_available}
        assigned_by_employee = {e: [] for e in employees_available}
        blocked_violations = []
        unknown_names = set()

        for day in DAYS:
            for name in manual_schedule[day]:
                if name not in employees_available:
                    unknown_names.add(name)
                    continue

                if day in employees_blocked[name]:
                    blocked_violations.append((name, day))

                assigned_days[name] += 1
                if day not in assigned_by_employee[name]:
                    assigned_by_employee[name].append(day)

        missing_min_days = [name for name, cnt in assigned_days.items() if cnt < MIN_TARGET]

        st.subheader("검증 결과")

        if invalid_lines:
            st.warning("형식 오류로 무시된 라인이 있습니다: " + ", ".join(invalid_lines))

        if unknown_names:
            st.warning("직원 목록에 없는 이름이 포함되어 있습니다: " + ", ".join(sorted(unknown_names)))

        if blocked_violations:
            st.error("출근 불가 요일에 배정된 항목이 있습니다.")
            for name, day in blocked_violations:
                st.write(f"- {name}: {day}요일 불가")
        else:
            st.success("출근 불가 요일 배정 없음")

        if missing_min_days:
            st.error("주 3일 이상 근무 조건을 충족하지 못한 인원이 있습니다.")
            for name in missing_min_days:
                st.write(f"- {name}: {assigned_days[name]}일 / 배정 요일 → {', '.join(assigned_by_employee[name]) if assigned_by_employee[name] else '배정 없음'}")
        else:
            st.success("모든 인원이 주 3일 이상 근무합니다.")

        st.subheader("직원별 배정 상세")
        for name in sorted(assigned_days.keys(), key=lambda x: assigned_days[x], reverse=True):
            days_list = assigned_by_employee[name]
            days_str = ", ".join(days_list) if days_list else "배정 없음"
            st.write(f"- {name}: {assigned_days[name]}일 / 배정 요일 → {days_str}")
