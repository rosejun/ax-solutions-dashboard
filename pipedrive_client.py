"""Pipedrive API Client - 대시보드 데이터 수집용"""

import requests
from config import API_TOKEN, BASE_URL_V1, BASE_URL_V2


class PipedriveClient:
    def __init__(self, api_token: str = None):
        self.api_token = api_token or API_TOKEN
        self.session = requests.Session()
        self.session.params = {"api_token": self.api_token}

    def _get_v1(self, endpoint: str, params: dict = None) -> dict:
        url = f"{BASE_URL_V1}/{endpoint}"
        resp = self.session.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _get_v2(self, endpoint: str, params: dict = None) -> dict:
        url = f"{BASE_URL_V2}/{endpoint}"
        resp = self.session.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _get_all_v2(self, endpoint: str, params: dict = None, limit: int = 100) -> list:
        """v2 API 페이지네이션 처리하여 전체 데이터 수집"""
        params = params or {}
        params["limit"] = limit
        all_items = []
        cursor = None

        while True:
            if cursor:
                params["cursor"] = cursor
            data = self._get_v2(endpoint, params)
            items = data.get("data", [])
            if not items:
                break
            all_items.extend(items)
            cursor = data.get("additional_data", {}).get("next_cursor")
            if not cursor:
                break

        return all_items

    # ── 파이프라인 & 스테이지 ──

    def get_pipelines(self) -> list:
        return self._get_v2("pipelines").get("data", [])

    def get_stages(self) -> list:
        return self._get_v1("stages").get("data", []) or []

    def get_stage_map(self) -> dict:
        """stage_id -> stage_name 매핑"""
        return {s["id"]: s["name"] for s in self.get_stages()}

    def get_pipeline_conversion_stats(self, pipeline_id: int, start_date: str, end_date: str) -> dict:
        """스테이지별 전환율 (start_date/end_date: YYYY-MM-DD)"""
        return self._get_v1(f"pipelines/{pipeline_id}/conversion_statistics", {
            "start_date": start_date,
            "end_date": end_date,
        })

    def get_pipeline_movement_stats(self, pipeline_id: int, start_date: str, end_date: str) -> dict:
        """딜 이동 통계"""
        return self._get_v1(f"pipelines/{pipeline_id}/movement_statistics", {
            "start_date": start_date,
            "end_date": end_date,
        })

    # ── 딜 ──

    def get_deals(self, pipeline_id: int = None, status: str = "open") -> list:
        params = {"status": status}
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        return self._get_all_v2("deals", params)

    def get_deals_summary(self, status: str = "open", pipeline_id: int = None) -> dict:
        params = {"status": status}
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        return self._get_v1("deals/summary", params)

    def get_deals_timeline(self, start_date: str, interval: str = "month",
                           amount: int = 12, field_key: str = "add_time",
                           pipeline_id: int = None) -> dict:
        """딜 타임라인 (interval: day/week/month/quarter)"""
        params = {
            "start_date": start_date,
            "interval": interval,
            "amount": amount,
            "field_key": field_key,
        }
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        return self._get_v1("deals/timeline", params)

    # ── 활동 ──

    def get_activities(self, user_id: int = None, done: bool = None) -> list:
        params = {}
        if user_id:
            params["user_id"] = user_id
        if done is not None:
            params["done"] = 1 if done else 0
        return self._get_all_v2("activities", params)

    # ── 목표 ──

    def get_goals(self, assignee_type: str = None) -> list:
        """목표 목록 (assignee_type: company/team/person)"""
        params = {}
        if assignee_type:
            params["type.name"] = assignee_type
        data = self._get_v1("goals/find", params).get("data", {})
        if isinstance(data, dict):
            return data.get("goals", []) or []
        return data or []

    def get_goal_results(self, goal_id: str, period_start: str, period_end: str) -> dict:
        return self._get_v1(f"goals/{goal_id}/results", {
            "period.start": period_start,
            "period.end": period_end,
        })

    # ── 사용자 ──

    def get_users(self) -> list:
        return self._get_v1("users").get("data", []) or []
