"""
Slack 알림 서비스

파이프라인 시작/완료/실패 알림을 Slack으로 전송합니다.

환경 변수:
    SLACK_WEBHOOK_URL: Slack Incoming Webhook URL
    SLACK_CHANNEL: 알림 채널 (기본: #data-pipeline)

사용법:
    from app.services.slack_notifier import SlackNotifier

    notifier = SlackNotifier()
    await notifier.send_pipeline_started("Q3", 2025)
    await notifier.send_pipeline_completed("Q3", 2025, stats)
    await notifier.send_pipeline_failed("Q3", 2025, error_message)
"""

import os
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#data-pipeline")


class SlackNotifier:
    """Slack 알림 서비스"""

    def __init__(self, webhook_url: str = None, channel: str = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        self.channel = channel or SLACK_CHANNEL
        self.enabled = bool(self.webhook_url)

        if not self.enabled:
            logger.warning("Slack 알림 비활성화: SLACK_WEBHOOK_URL 미설정")

    async def _send_message(self, payload: Dict[str, Any]) -> bool:
        """Slack 메시지 전송"""
        if not self.enabled:
            logger.info(f"[Slack 비활성화] {payload.get('text', '')[:50]}...")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Slack 전송 실패: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Slack 전송 오류: {e}")
            return False

    async def send_pipeline_started(self, quarter: str, year: int) -> bool:
        """파이프라인 시작 알림"""
        payload = {
            "channel": self.channel,
            "username": "RaymondsData Bot",
            "icon_emoji": ":rocket:",
            "attachments": [
                {
                    "color": "#36a64f",
                    "title": f"📊 분기 파이프라인 시작",
                    "fields": [
                        {"title": "분기", "value": f"{year}년 {quarter}", "short": True},
                        {"title": "시작 시각", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                    ],
                    "footer": "Raymontology Data Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        return await self._send_message(payload)

    async def send_pipeline_completed(
        self,
        quarter: str,
        year: int,
        stats: Dict[str, Any],
        duration_seconds: int = None
    ) -> bool:
        """파이프라인 완료 알림"""
        duration_str = ""
        if duration_seconds:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            duration_str = f"{hours}시간 {minutes}분"

        fields = [
            {"title": "분기", "value": f"{year}년 {quarter}", "short": True},
            {"title": "상태", "value": "✅ 완료", "short": True}
        ]

        if duration_str:
            fields.append({"title": "소요 시간", "value": duration_str, "short": True})

        # 통계 필드 추가
        if stats:
            if stats.get('companies_processed'):
                fields.append({"title": "처리 기업", "value": f"{stats['companies_processed']:,}개", "short": True})
            if stats.get('officers_inserted'):
                fields.append({"title": "신규 임원", "value": f"{stats['officers_inserted']:,}명", "short": True})
            if stats.get('positions_inserted'):
                fields.append({"title": "신규 포지션", "value": f"{stats['positions_inserted']:,}개", "short": True})

        payload = {
            "channel": self.channel,
            "username": "RaymondsData Bot",
            "icon_emoji": ":white_check_mark:",
            "attachments": [
                {
                    "color": "#2eb886",
                    "title": f"✅ 분기 파이프라인 완료",
                    "fields": fields,
                    "footer": "Raymontology Data Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        return await self._send_message(payload)

    async def send_pipeline_failed(
        self,
        quarter: str,
        year: int,
        error_message: str,
        step: str = None
    ) -> bool:
        """파이프라인 실패 알림"""
        fields = [
            {"title": "분기", "value": f"{year}년 {quarter}", "short": True},
            {"title": "상태", "value": "❌ 실패", "short": True}
        ]

        if step:
            fields.append({"title": "실패 단계", "value": step, "short": True})

        fields.append({"title": "오류 메시지", "value": f"```{error_message[:500]}```", "short": False})

        payload = {
            "channel": self.channel,
            "username": "RaymondsData Bot",
            "icon_emoji": ":x:",
            "attachments": [
                {
                    "color": "#dc3545",
                    "title": f"❌ 분기 파이프라인 실패",
                    "fields": fields,
                    "footer": "Raymontology Data Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        return await self._send_message(payload)

    async def send_custom_message(
        self,
        title: str,
        message: str,
        color: str = "#3498db",
        emoji: str = ":bell:"
    ) -> bool:
        """커스텀 알림 메시지"""
        payload = {
            "channel": self.channel,
            "username": "RaymondsData Bot",
            "icon_emoji": emoji,
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "Raymontology Data Pipeline",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        return await self._send_message(payload)


# 싱글톤 인스턴스
_notifier: Optional[SlackNotifier] = None


def get_slack_notifier() -> SlackNotifier:
    """SlackNotifier 싱글톤 인스턴스 반환"""
    global _notifier
    if _notifier is None:
        _notifier = SlackNotifier()
    return _notifier
