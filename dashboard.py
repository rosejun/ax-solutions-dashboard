"""Pipedrive Insights 대시보드 데이터 수집 및 출력"""

from datetime import datetime, timedelta
from collections import defaultdict
from pipedrive_client import PipedriveClient


def format_currency(value: float) -> str:
    return f"{value:,.0f}"


class PipedriveDashboard:
    def __init__(self, api_token: str = None):
        self.client = PipedriveClient(api_token)
        today = datetime.now()
        self.today = today.strftime("%Y-%m-%d")
        self.month_start = today.replace(day=1).strftime("%Y-%m-%d")
        self.year_start = today.replace(month=1, day=1).strftime("%Y-%m-%d")

        # 스테이지/사용자 이름 매핑 캐시
        self.stage_map = self.client.get_stage_map()
        try:
            users = self.client.get_users()
            self.user_map = {u["id"]: u.get("name", f"User {u['id']}") for u in users}
        except Exception:
            self.user_map = {}

    # ═══════════════════════════════════════════
    # 1. 영업 파이프라인 현황
    # ═══════════════════════════════════════════

    def pipeline_overview(self):
        """파이프라인별 딜 현황 + 전환율"""
        print("\n" + "=" * 60)
        print("  1. 영업 파이프라인 현황")
        print("=" * 60)

        pipelines = self.client.get_pipelines()
        for pipeline in pipelines:
            pid = pipeline["id"]
            name = pipeline["name"]
            print(f"\n  [{name}] (ID: {pid})")
            print("-" * 40)

            # 딜 현황 - 스테이지별 집계
            deals = self.client.get_deals(pipeline_id=pid)
            stage_deals = defaultdict(list)
            for deal in deals:
                sid = deal.get("stage_id", 0)
                stage_deals[sid].append(deal)

            total_value = sum(d.get("value", 0) or 0 for d in deals)
            print(f"  총 딜 수: {len(deals)}개 | 총 금액: {format_currency(total_value)}원")

            if stage_deals:
                print("  [스테이지별 딜]")
                for sid, sd in stage_deals.items():
                    sname = self.stage_map.get(sid, f"Stage {sid}")
                    sval = sum(d.get("value", 0) or 0 for d in sd)
                    print(f"    {sname}: {len(sd)}건 ({format_currency(sval)}원)")

            # 전환율
            try:
                conv = self.client.get_pipeline_conversion_stats(pid, self.year_start, self.today)
                conv_data = conv.get("data", {})
                if conv_data:
                    stage_conversions = conv_data.get("stage_conversions", [])
                    non_zero = [sc for sc in stage_conversions if sc.get("conversion_rate", 0) > 0]
                    if non_zero:
                        print("  [전환율]")
                        for sc in non_zero:
                            from_stage = self.stage_map.get(sc.get("from_stage_id"), "?")
                            to_stage = self.stage_map.get(sc.get("to_stage_id"), "?")
                            rate = sc.get("conversion_rate", 0)
                            print(f"    {from_stage} -> {to_stage}: {rate}%")
                    won_rate = conv_data.get("won_conversion", 0)
                    lost_rate = conv_data.get("lost_conversion", 0)
                    if won_rate or lost_rate:
                        print(f"  성사율: {won_rate}% | 실패율: {lost_rate}%")
            except Exception as e:
                print(f"  (전환율 조회 실패: {e})")

            # 딜 이동 통계
            try:
                mov = self.client.get_pipeline_movement_stats(pid, self.month_start, self.today)
                mov_data = mov.get("data", {})
                if mov_data:
                    new_count = mov_data.get("new_deals_count", 0)
                    won_count = mov_data.get("deals_won_count", 0)
                    lost_count = mov_data.get("deals_lost_count", 0)
                    avg_age = mov_data.get("average_age_in_days", {}).get("across_all_stages", 0)
                    print(f"  이번 달: 신규 {new_count} | 성사 {won_count} | 실패 {lost_count} | 평균 소요일 {avg_age}일")
            except Exception as e:
                print(f"  (이동 통계 조회 실패: {e})")

    # ═══════════════════════════════════════════
    # 2. 매출/수익 분석
    # ═══════════════════════════════════════════

    def revenue_analysis(self):
        """매출 요약 및 트렌드"""
        print("\n" + "=" * 60)
        print("  2. 매출/수익 분석")
        print("=" * 60)

        # 딜 요약 (성사된 딜)
        won_summary = self.client.get_deals_summary(status="won")
        won_data = won_summary.get("data", {})
        if won_data:
            total = won_data.get("total_count", 0)
            values = won_data.get("total_currency_converted_value", 0)
            print(f"\n  [성사된 딜]")
            print(f"  총 건수: {total}건 | 총 금액: {format_currency(values)}원")

        # 진행 중 딜
        open_summary = self.client.get_deals_summary(status="open")
        open_data = open_summary.get("data", {})
        if open_data:
            total = open_data.get("total_count", 0)
            values = open_data.get("total_currency_converted_value", 0)
            weighted = open_data.get("total_weighted_currency_converted_value", 0)
            print(f"\n  [진행 중인 딜]")
            print(f"  총 건수: {total}건 | 총 금액: {format_currency(values)}원")
            print(f"  가중 예상 금액: {format_currency(weighted)}원")

        # 월별 트렌드
        print(f"\n  [월별 성사 딜 트렌드 (올해)]")
        try:
            timeline = self.client.get_deals_timeline(
                start_date=self.year_start,
                interval="month",
                amount=12,
                field_key="won_time",
            )
            tl_data = timeline.get("data", [])
            for period in tl_data:
                period_start = period.get("period_start", "")
                deals_list = period.get("deals", [])
                count = len(deals_list) if isinstance(deals_list, list) else 0
                total_values = period.get("total_values", {})
                # total_values는 통화별 dict
                value_str = ""
                if isinstance(total_values, dict):
                    for currency, val in total_values.items():
                        value_str += f" {format_currency(val)}원"
                month_label = period_start[:7] if period_start else "?"
                if count > 0:
                    print(f"    {month_label}: {count}건 |{value_str}")
                else:
                    print(f"    {month_label}: -")
        except Exception as e:
            print(f"  (트렌드 조회 실패: {e})")

        # 목표 달성률
        goals = self.client.get_goals()
        if goals:
            print(f"\n  [목표 달성률]")
            for goal in goals:
                gid = goal.get("id")
                title = goal.get("title", "무제")
                try:
                    results = self.client.get_goal_results(gid, self.year_start, self.today)
                    result_data = results.get("data", {})
                    progress = result_data.get("progress_percentage", "N/A")
                    print(f"    {title}: {progress}%")
                except Exception:
                    print(f"    {title}: (결과 조회 실패)")
        else:
            print(f"\n  [목표] 설정된 목표 없음")

    # ═══════════════════════════════════════════
    # 3. 활동/성과 분석
    # ═══════════════════════════════════════════

    def activity_analysis(self):
        """담당자별 활동 분석"""
        print("\n" + "=" * 60)
        print("  3. 활동/성과 분석")
        print("=" * 60)

        activities = self.client.get_activities()

        # 타입별 집계
        by_type = defaultdict(int)
        by_user = defaultdict(lambda: {"done": 0, "pending": 0, "total": 0})

        for act in activities:
            act_type = act.get("type", "unknown")
            by_type[act_type] += 1

            user_id = act.get("owner_id", "unknown")
            by_user[user_id]["total"] += 1
            if act.get("done"):
                by_user[user_id]["done"] += 1
            else:
                by_user[user_id]["pending"] += 1

        print(f"\n  [활동 타입별 현황] (총 {len(activities)}건)")
        for act_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"    {act_type}: {count}건")

        print(f"\n  [담당자별 활동 현황]")
        for user_id, stats in sorted(by_user.items(), key=lambda x: -x[1]["total"]):
            name = self.user_map.get(user_id, f"User {user_id}")
            done_rate = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"    {name}: 총 {stats['total']}건 (완료 {stats['done']} / 미완 {stats['pending']}) - 완료율 {done_rate:.0f}%")

    # ═══════════════════════════════════════════
    # 전체 대시보드 실행
    # ═══════════════════════════════════════════

    def run(self):
        print("\n" + "#" * 60)
        print("  Pipedrive Insights Dashboard")
        print(f"  생성일: {self.today}")
        print("#" * 60)

        self.pipeline_overview()
        self.revenue_analysis()
        self.activity_analysis()

        print("\n" + "#" * 60)
        print("  대시보드 출력 완료")
        print("#" * 60 + "\n")


if __name__ == "__main__":
    dashboard = PipedriveDashboard()
    dashboard.run()
