"""
이메일 서비스 (SendGrid)
"""
import logging
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """SendGrid 기반 이메일 발송 서비스"""

    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.email_from_address
        self.from_name = settings.email_from_name
        self.frontend_url = settings.frontend_url

    @property
    def is_configured(self) -> bool:
        """SendGrid가 설정되어 있는지 확인"""
        return bool(self.api_key)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """이메일 발송"""
        if not self.is_configured:
            logger.warning("SendGrid API key not configured. Email not sent.")
            # 개발 환경에서는 콘솔에 출력
            logger.info(f"[DEV] Email to: {to_email}")
            logger.info(f"[DEV] Subject: {subject}")
            logger.info(f"[DEV] Content: {html_content[:200]}...")
            return True  # 개발 환경에서는 성공으로 처리

        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            if plain_content:
                message.add_content(Content("text/plain", plain_content))

            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

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


# 싱글톤 인스턴스
email_service = EmailService()
