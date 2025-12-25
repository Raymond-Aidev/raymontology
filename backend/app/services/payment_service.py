"""
Payment Service - 결제 서비스 인터페이스 및 구현체
결제 대행사(PG) 연동을 위한 추상화 레이어
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PaymentResult:
    """결제 결과"""
    def __init__(
        self,
        success: bool,
        transaction_id: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.transaction_id = transaction_id
        self.message = message
        self.data = data or {}


class PaymentService(ABC):
    """결제 서비스 추상 클래스"""

    @abstractmethod
    async def create_payment(
        self,
        order_id: str,
        amount: int,
        order_name: str,
        customer_email: str,
        customer_name: str,
        success_url: str,
        fail_url: str
    ) -> Dict[str, Any]:
        """
        결제 요청 생성
        Returns: checkout_url, client_key 등 PG사별 응답
        """
        pass

    @abstractmethod
    async def verify_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int
    ) -> PaymentResult:
        """
        결제 승인/확인
        PG사에서 리다이렉트 후 최종 승인
        """
        pass

    @abstractmethod
    async def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str
    ) -> PaymentResult:
        """결제 취소"""
        pass

    @abstractmethod
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> PaymentResult:
        """웹훅 처리"""
        pass


class TossPaymentsService(PaymentService):
    """
    토스페이먼츠 결제 서비스
    https://docs.tosspayments.com/
    """

    def __init__(self):
        self.secret_key = settings.toss_payments_secret_key
        self.client_key = settings.toss_payments_client_key
        self.base_url = "https://api.tosspayments.com/v1"

    def _get_headers(self) -> Dict[str, str]:
        """인증 헤더 생성"""
        import base64
        auth = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }

    async def create_payment(
        self,
        order_id: str,
        amount: int,
        order_name: str,
        customer_email: str,
        customer_name: str,
        success_url: str,
        fail_url: str
    ) -> Dict[str, Any]:
        """
        토스페이먼츠 결제 요청 생성
        프론트엔드에서 토스페이먼츠 SDK를 사용하여 결제창 호출
        """
        # 토스페이먼츠는 프론트엔드 SDK 방식이므로
        # 백엔드에서는 client_key만 전달
        return {
            "order_id": order_id,
            "amount": amount,
            "order_name": order_name,
            "client_key": self.client_key,
            "success_url": success_url,
            "fail_url": fail_url
        }

    async def verify_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int
    ) -> PaymentResult:
        """
        토스페이먼츠 결제 승인
        https://docs.tosspayments.com/reference#결제-승인
        """
        if not self.secret_key:
            logger.warning("TossPayments secret key not configured")
            return PaymentResult(
                success=False,
                message="결제 시스템이 설정되지 않았습니다."
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments/confirm",
                    headers=self._get_headers(),
                    json={
                        "paymentKey": payment_key,
                        "orderId": order_id,
                        "amount": amount
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return PaymentResult(
                        success=True,
                        transaction_id=data.get("paymentKey"),
                        message="결제가 완료되었습니다.",
                        data=data
                    )
                else:
                    error_data = response.json()
                    return PaymentResult(
                        success=False,
                        message=error_data.get("message", "결제 승인에 실패했습니다."),
                        data=error_data
                    )
        except Exception as e:
            logger.error(f"TossPayments verify error: {e}")
            return PaymentResult(
                success=False,
                message=f"결제 처리 중 오류가 발생했습니다: {str(e)}"
            )

    async def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str
    ) -> PaymentResult:
        """토스페이먼츠 결제 취소"""
        if not self.secret_key:
            return PaymentResult(success=False, message="결제 시스템이 설정되지 않았습니다.")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments/{payment_key}/cancel",
                    headers=self._get_headers(),
                    json={"cancelReason": cancel_reason}
                )

                if response.status_code == 200:
                    return PaymentResult(
                        success=True,
                        message="결제가 취소되었습니다.",
                        data=response.json()
                    )
                else:
                    error_data = response.json()
                    return PaymentResult(
                        success=False,
                        message=error_data.get("message", "결제 취소에 실패했습니다.")
                    )
        except Exception as e:
            logger.error(f"TossPayments cancel error: {e}")
            return PaymentResult(success=False, message=str(e))

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> PaymentResult:
        """토스페이먼츠 웹훅 처리"""
        # 웹훅 시그니처 검증 (프로덕션에서 필수)
        event_type = payload.get("eventType")
        data = payload.get("data", {})

        if event_type == "PAYMENT_STATUS_CHANGED":
            status = data.get("status")
            payment_key = data.get("paymentKey")

            return PaymentResult(
                success=True,
                transaction_id=payment_key,
                message=f"결제 상태 변경: {status}",
                data=data
            )

        return PaymentResult(
            success=True,
            message=f"웹훅 수신: {event_type}"
        )


class MockPaymentService(PaymentService):
    """
    테스트용 Mock 결제 서비스
    개발/테스트 환경에서 사용
    """

    async def create_payment(
        self,
        order_id: str,
        amount: int,
        order_name: str,
        customer_email: str,
        customer_name: str,
        success_url: str,
        fail_url: str
    ) -> Dict[str, Any]:
        """Mock 결제 생성"""
        return {
            "order_id": order_id,
            "amount": amount,
            "order_name": order_name,
            "client_key": "mock_client_key",
            "checkout_url": f"{success_url}?orderId={order_id}&paymentKey=mock_payment_key_{uuid.uuid4().hex[:8]}&amount={amount}",
            "is_mock": True
        }

    async def verify_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int
    ) -> PaymentResult:
        """Mock 결제 승인 - 항상 성공"""
        return PaymentResult(
            success=True,
            transaction_id=payment_key,
            message="[테스트] 결제가 완료되었습니다.",
            data={"mock": True}
        )

    async def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str
    ) -> PaymentResult:
        """Mock 결제 취소"""
        return PaymentResult(
            success=True,
            message="[테스트] 결제가 취소되었습니다."
        )

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> PaymentResult:
        """Mock 웹훅 처리"""
        return PaymentResult(success=True, message="[테스트] 웹훅 수신")


def get_payment_service() -> PaymentService:
    """
    결제 서비스 인스턴스 반환
    환경 설정에 따라 적절한 서비스 선택
    """
    pg_provider = settings.pg_provider

    if pg_provider == "tosspayments":
        return TossPaymentsService()
    elif pg_provider == "mock":
        return MockPaymentService()
    else:
        # 기본값: Mock (개발 환경)
        logger.warning(f"Unknown PG provider '{pg_provider}', using MockPaymentService")
        return MockPaymentService()
