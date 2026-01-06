"""
이메일 서비스 (Gmail SMTP)
"""
import logging
import smtplib
import ssl
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from app.config import settings

logger = logging.getLogger(__name__)

# Thread pool for synchronous SMTP operations
_executor = ThreadPoolExecutor(max_workers=3)


class EmailService:
    """Gmail SMTP 기반 이메일 발송 서비스"""

    def __init__(self):
        self.smtp_email = settings.smtp_email
        self.smtp_password = settings.smtp_password
        self.from_email = settings.email_from_address
        self.from_name = settings.email_from_name
        self.frontend_url = settings.frontend_url

    @property
    def is_configured(self) -> bool:
        """Gmail SMTP가 설정되어 있는지 확인"""
        return bool(self.smtp_email and self.smtp_password)

    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """동기 이메일 발송 (스레드에서 실행)"""
        try:
            # 이메일 메시지 생성
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.smtp_email}>"
            message["To"] = to_email

            # Plain text 버전 추가
            if plain_content:
                part1 = MIMEText(plain_content, "plain", "utf-8")
                message.attach(part1)

            # HTML 버전 추가
            part2 = MIMEText(html_content, "html", "utf-8")
            message.attach(part2)

            # Gmail SMTP로 발송 (포트 587 + STARTTLS, 타임아웃 30초)
            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls(context=context)
                server.login(self.smtp_email, self.smtp_password)
                server.sendmail(self.smtp_email, to_email, message.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """비동기 이메일 발송"""
        if not self.is_configured:
            logger.warning("Gmail SMTP not configured. Email not sent.")
            logger.info(f"[DEV] Email to: {to_email}")
            logger.info(f"[DEV] Subject: {subject}")
            logger.info(f"[DEV] Content: {html_content[:200]}...")
            return True

        # 동기 SMTP 작업을 스레드 풀에서 실행
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._send_email_sync,
            to_email,
            subject,
            html_content,
            plain_content
        )

    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """비밀번호 재설정 이메일 발송"""
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"

        subject = "[Raymontology] 비밀번호 재설정 요청"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #3B82F6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .button:hover {{ background: #2563EB; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">Raymontology</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">비밀번호 재설정</p>
                </div>
                <div class="content">
                    <p>안녕하세요,</p>
                    <p>비밀번호 재설정을 요청하셨습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정해주세요.</p>

                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">비밀번호 재설정</a>
                    </div>

                    <p>또는 아래 링크를 브라우저에 직접 입력하세요:</p>
                    <p style="word-break: break-all; font-size: 14px; color: #6b7280;">{reset_url}</p>

                    <div class="warning">
                        <strong>주의:</strong> 이 링크는 1시간 동안만 유효합니다.
                        비밀번호 재설정을 요청하지 않으셨다면 이 이메일을 무시하셔도 됩니다.
                    </div>
                </div>
                <div class="footer">
                    <p>이 이메일은 Raymontology에서 자동으로 발송되었습니다.</p>
                    <p>&copy; 2025 Raymontology. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        비밀번호 재설정

        안녕하세요,

        비밀번호 재설정을 요청하셨습니다. 아래 링크를 클릭하여 새 비밀번호를 설정해주세요.

        {reset_url}

        이 링크는 1시간 동안만 유효합니다.
        비밀번호 재설정을 요청하지 않으셨다면 이 이메일을 무시하셔도 됩니다.

        Raymontology 팀 드림
        """

        return await self.send_email(to_email, subject, html_content, plain_content)


    async def send_verification_email(self, to_email: str, verification_token: str, username: str) -> bool:
        """회원가입 이메일 인증 발송"""
        verify_url = f"{self.frontend_url}/verify-email?token={verification_token}"

        subject = "[RaymondsRisk] 이메일 인증을 완료해주세요"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #10B981; color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; font-size: 16px; }}
                .button:hover {{ background: #059669; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                .info {{ background: #dbeafe; border: 1px solid #3b82f6; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">RaymondsRisk</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">이메일 인증</p>
                </div>
                <div class="content">
                    <p>안녕하세요, <strong>{username}</strong>님!</p>
                    <p>RaymondsRisk 회원가입을 환영합니다. 아래 버튼을 클릭하여 이메일 인증을 완료해주세요.</p>

                    <div style="text-align: center;">
                        <a href="{verify_url}" class="button">가입 확인</a>
                    </div>

                    <p>또는 아래 링크를 브라우저에 직접 입력하세요:</p>
                    <p style="word-break: break-all; font-size: 14px; color: #6b7280;">{verify_url}</p>

                    <div class="info">
                        <strong>안내:</strong> 이 링크는 24시간 동안 유효합니다.
                        회원가입을 요청하지 않으셨다면 이 이메일을 무시하셔도 됩니다.
                    </div>
                </div>
                <div class="footer">
                    <p>이 이메일은 RaymondsRisk에서 자동으로 발송되었습니다.</p>
                    <p>&copy; 2025 RaymondsRisk. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        이메일 인증

        안녕하세요, {username}님!

        RaymondsRisk 회원가입을 환영합니다. 아래 링크를 클릭하여 이메일 인증을 완료해주세요.

        {verify_url}

        이 링크는 24시간 동안 유효합니다.
        회원가입을 요청하지 않으셨다면 이 이메일을 무시하셔도 됩니다.

        RaymondsRisk 팀 드림
        """

        return await self.send_email(to_email, subject, html_content, plain_content)

    # ========================================================================
    # 서비스 이용신청 관련 이메일
    # ========================================================================

    async def send_service_application_email(
        self,
        to_email: str,
        plan_type: str,
        plan_name: str,
        plan_amount: int
    ) -> bool:
        """
        서비스 이용신청 완료 이메일 (사용자에게)
        입금 안내 포함
        """
        from datetime import datetime

        subject = "[레이먼파트너스] 서비스 이용신청 접수 및 입금 안내"

        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.8; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1E40AF, #3B82F6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; border: 1px solid #e5e7eb; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .info-box h3 {{ margin: 0 0 15px 0; color: #1f2937; font-size: 16px; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }}
                .info-row:last-child {{ border-bottom: none; }}
                .info-label {{ color: #6b7280; }}
                .info-value {{ color: #1f2937; font-weight: 500; }}
                .bank-info {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .bank-info h3 {{ margin: 0 0 15px 0; color: #92400e; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                .amount {{ font-size: 24px; color: #1E40AF; font-weight: 700; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">레이먼파트너스</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">서비스 이용신청 접수 완료</p>
                </div>
                <div class="content">
                    <p>안녕하세요, 레이먼파트너스입니다.</p>
                    <p>서비스 이용신청이 접수되었습니다.</p>

                    <div class="info-box">
                        <h3>신청 정보</h3>
                        <div class="info-row">
                            <span class="info-label">신청일시</span>
                            <span class="info-value">{current_time}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">신청 플랜</span>
                            <span class="info-value">{plan_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">결제 금액</span>
                            <span class="info-value amount">{plan_amount:,}원</span>
                        </div>
                    </div>

                    <div class="bank-info">
                        <h3>입금 안내</h3>
                        <div class="info-row">
                            <span class="info-label">사명</span>
                            <span class="info-value">코넥트</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">사업자등록번호</span>
                            <span class="info-value">686-19-02309</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">입금계좌</span>
                            <span class="info-value">카카오뱅크 3333-31-9041159</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">예금주</span>
                            <span class="info-value">코넥트 / 박재준</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">입금액</span>
                            <span class="info-value" style="color: #DC2626; font-weight: 700;">{plan_amount:,}원</span>
                        </div>
                    </div>

                    <p>입금 확인 후 서비스 이용이 가능합니다.</p>
                    <p>문의사항은 이 이메일로 회신 부탁드립니다.</p>

                    <p>감사합니다.</p>
                </div>
                <div class="footer">
                    <p>이 이메일은 레이먼파트너스에서 자동으로 발송되었습니다.</p>
                    <p>&copy; 2025 레이먼파트너스. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        [레이먼파트너스] 서비스 이용신청 접수 및 입금 안내

        안녕하세요, 레이먼파트너스입니다.

        서비스 이용신청이 접수되었습니다.

        ■ 신청 정보
        - 신청일시: {current_time}
        - 신청 플랜: {plan_name}
        - 결제 금액: {plan_amount:,}원

        ■ 입금 안내
        - 사명: 코넥트
        - 사업자등록번호: 686-19-02309
        - 입금계좌: 카카오뱅크 3333-31-9041159 (코넥트 / 박재준)
        - 입금액: {plan_amount:,}원

        입금 확인 후 서비스 이용이 가능합니다.
        문의사항은 이 이메일로 회신 부탁드립니다.

        감사합니다.
        """

        return await self.send_email(to_email, subject, html_content, plain_content)

    async def send_admin_application_notification(
        self,
        applicant_email: str,
        plan_name: str,
        plan_amount: int,
        application_id: str
    ) -> bool:
        """관리자에게 새 신청 알림 이메일"""
        from datetime import datetime

        admin_email = "raymond.jj.park@proton.me"
        subject = f"[신규 서비스 신청] {applicant_email} - {plan_name}"

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #DC2626; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: white; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">신규 서비스 신청</h2>
                </div>
                <div class="content">
                    <div class="info-box">
                        <p><strong>신청자:</strong> {applicant_email}</p>
                        <p><strong>플랜:</strong> {plan_name} ({plan_amount:,}원)</p>
                        <p><strong>신청일시:</strong> {current_time}</p>
                        <p><strong>신청 ID:</strong> {application_id}</p>
                    </div>
                    <p>관리자 페이지에서 확인해주세요:</p>
                    <a href="{self.frontend_url}/admin" class="button">관리자 페이지 바로가기</a>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        [신규 서비스 신청] {applicant_email} - {plan_name}

        ■ 신청 정보
        - 신청자: {applicant_email}
        - 플랜: {plan_name} ({plan_amount:,}원)
        - 신청일시: {current_time}

        관리자 페이지에서 확인해주세요:
        {self.frontend_url}/admin
        """

        return await self.send_email(admin_email, subject, html_content, plain_content)

    async def send_payment_confirmed_email(self, to_email: str) -> bool:
        """입금 확인 이메일 (사용자에게)"""
        subject = "[레이먼파트너스] 입금 확인 완료"

        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                .content { background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }
                .success-icon { font-size: 48px; margin-bottom: 15px; }
                .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✓</div>
                    <h1 style="margin: 0; font-size: 24px;">입금 확인 완료</h1>
                </div>
                <div class="content">
                    <p>안녕하세요,</p>
                    <p>입금이 확인되었습니다.</p>
                    <p>이용권 승인 처리 후 서비스를 이용하실 수 있습니다.</p>
                    <p>승인이 완료되면 별도 이메일로 안내드리겠습니다.</p>
                    <p>감사합니다.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 레이먼파트너스. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = """
        [레이먼파트너스] 입금 확인 완료

        안녕하세요,

        입금이 확인되었습니다.
        이용권 승인 처리 후 서비스를 이용하실 수 있습니다.

        승인이 완료되면 별도 이메일로 안내드리겠습니다.

        감사합니다.
        """

        return await self.send_email(to_email, subject, html_content, plain_content)

    async def send_subscription_approved_email(
        self,
        to_email: str,
        start_date,
        end_date
    ) -> bool:
        """이용권 승인 완료 이메일 (사용자에게)"""
        subject = "[레이먼파트너스] 서비스 이용권 발급 완료"

        start_str = start_date.strftime("%Y년 %m월 %d일") if hasattr(start_date, 'strftime') else str(start_date)
        end_str = end_date.strftime("%Y년 %m월 %d일") if hasattr(end_date, 'strftime') else str(end_date)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1E40AF, #3B82F6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success-icon {{ font-size: 48px; margin-bottom: 15px; }}
                .info-box {{ background: white; border: 1px solid #10B981; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .button {{ display: inline-block; background: #3B82F6; color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">🎉</div>
                    <h1 style="margin: 0; font-size: 24px;">서비스 이용권 발급 완료!</h1>
                </div>
                <div class="content">
                    <p>안녕하세요,</p>
                    <p>서비스 이용권이 발급되었습니다.</p>

                    <div class="info-box">
                        <h3 style="margin: 0 0 15px 0; color: #059669;">이용 기간</h3>
                        <p style="margin: 5px 0;"><strong>시작일:</strong> {start_str}</p>
                        <p style="margin: 5px 0;"><strong>종료일:</strong> {end_str}</p>
                    </div>

                    <p>지금 바로 서비스를 이용해보세요!</p>

                    <div style="text-align: center;">
                        <a href="{self.frontend_url}" class="button">서비스 바로가기</a>
                    </div>

                    <p>감사합니다.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 레이먼파트너스. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        [레이먼파트너스] 서비스 이용권 발급 완료

        안녕하세요,

        서비스 이용권이 발급되었습니다.

        ■ 이용 기간
        - 시작일: {start_str}
        - 종료일: {end_str}

        지금 바로 서비스를 이용해보세요!
        {self.frontend_url}

        감사합니다.
        """

        return await self.send_email(to_email, subject, html_content, plain_content)

    async def send_application_rejected_email(
        self,
        to_email: str,
        reason: str = None
    ) -> bool:
        """신청 거절 이메일 (사용자에게)"""
        subject = "[레이먼파트너스] 서비스 이용신청 결과 안내"

        reason_text = reason if reason else "상세 사유는 별도 문의 부탁드립니다."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #6B7280; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .reason-box {{ background: #fef2f2; border: 1px solid #fca5a5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 24px;">서비스 이용신청 결과</h1>
                </div>
                <div class="content">
                    <p>안녕하세요,</p>
                    <p>서비스 이용신청을 검토한 결과, 신청이 승인되지 않았습니다.</p>

                    <div class="reason-box">
                        <strong>사유:</strong><br>
                        {reason_text}
                    </div>

                    <p>추가 문의사항이 있으시면 이 이메일로 회신해주세요.</p>
                    <p>감사합니다.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 레이먼파트너스. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
        [레이먼파트너스] 서비스 이용신청 결과 안내

        안녕하세요,

        서비스 이용신청을 검토한 결과, 신청이 승인되지 않았습니다.

        사유: {reason_text}

        추가 문의사항이 있으시면 이 이메일로 회신해주세요.

        감사합니다.
        """

        return await self.send_email(to_email, subject, html_content, plain_content)


# 싱글톤 인스턴스
email_service = EmailService()
