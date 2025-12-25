"""
Content 모델 - 페이지 콘텐츠 관리
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class PageContent(Base):
    """
    페이지 콘텐츠 테이블
    서비스 소개, 기능 설명 등의 텍스트/이미지를 관리
    """
    __tablename__ = "page_contents"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 콘텐츠 식별
    page = Column(String(50), nullable=False, index=True)      # 'about', 'features', 'home'
    section = Column(String(50), nullable=False, index=True)   # 'hero', 'feature1', 'advantage1'
    field = Column(String(50), nullable=False, index=True)     # 'title', 'description', 'image'

    # 콘텐츠 값
    value = Column(Text, nullable=True)                        # 텍스트 또는 이미지 URL

    # 메타데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<PageContent(page='{self.page}', section='{self.section}', field='{self.field}')>"


# 콘텐츠 기본값 정의 (초기 데이터)
DEFAULT_ABOUT_CONTENT = {
    "hero": {
        "badge": "투자 인텔리전스 플랫폼",
        "title": "숨겨진 관계망을 AI로 분석하여\n투자 리스크를 조기 발견",
        "description": "공시 자료만으로는 파악할 수 없는 임원의 과거 경력, CB 인수자의 다른 참여 기업, 대주주의 특수관계인 네트워크를 3단계 관계망으로 자동 시각화합니다.",
    },
    "why_section": {
        "title": "왜 RaymondsRisk인가요?",
        "description": "기관투자자만 접근하던 정보를 개인투자자도 동등하게 이용할 수 있습니다.",
    },
    "advantage1": {
        "title": "정보 비대칭 해소",
        "description": "기관투자자는 전문 실사팀과 고가의 터미널로 기업을 분석하지만, 개인투자자는 공시 자료에만 의존합니다. RaymondsRisk는 이러한 정보 격차를 해소합니다.",
    },
    "advantage2": {
        "title": "특허 기술 기반 신뢰성",
        "description": "대한민국 특허청에 출원 중인 '3단계 계층적 관계망 시각화' 및 '포트폴리오 학습 시스템' 특허 기술을 기반으로, 1.5초 이내에 복잡한 관계망을 구축하고 78.3% 정확도로 리스크를 예측합니다.",
    },
    "advantage3": {
        "title": "실시간 업데이트",
        "description": "CB 발행, 대표이사 변경, 대주주 변동, 거래량 급증 등 7가지 위험 신호를 실시간으로 업데이트합니다. 시장 변화에 신속하게 대응할 수 있습니다.",
    },
    "advantage4": {
        "title": "합법적이고 투명한 데이터",
        "description": "금융감독원 DART, 한국거래소 KRX, 대법원 판결문 등 모두 공개된 합법적 데이터만 사용합니다. 불법 내부정보는 절대 활용하지 않으며 PIPA를 완벽히 준수합니다.",
    },
    "advantage5": {
        "title": "접근성과 경제성",
        "description": "합리적인 가격으로 기관투자자 수준의 분석 도구를 이용할 수 있으며, 간편하게 시작할 수 있습니다.",
    },
    "features_section": {
        "title": "주요 기능",
        "description": "AI 기반 관계망 분석부터 실시간 모니터링까지, 투자 의사결정에 필요한 모든 기능을 제공합니다.",
    },
    "feature1": {
        "badge": "기능 1",
        "title": "3단계 관계망 자동 분석",
        "description": "검색창에 종목코드나 기업명만 입력하면, AI가 자동으로 3단계 관계망을 1.5초 만에 구축합니다.",
        "image": "",  # 이미지 URL
    },
    "feature2": {
        "badge": "기능 2",
        "title": "AI 리스크 조기 경고",
        "description": "500개 이상의 부실 기업 패턴을 학습한 AI가 40개 이상의 변수를 종합 분석하여 0~100점의 리스크 점수를 산출합니다.",
        "image": "",
    },
    "feature3": {
        "badge": "기능 3",
        "title": "포트폴리오 주가 패턴 예측",
        "description": "관계망으로 연결된 기업들을 묶어 포트폴리오로 저장하면, AI가 30차원 특징을 자동 추출하여 30일 후 수익률을 예측합니다.",
        "image": "",
    },
    "feature4": {
        "badge": "기능 4",
        "title": "24시간 실시간 모니터링",
        "description": "내 포트폴리오에 등록된 모든 기업을 24시간 자동 감시하며, 7가지 이벤트 발생 시 즉시 알림을 발송합니다.",
        "image": "",
    },
    "stats_section": {
        "title": "검증된 성과",
    },
    "cta_section": {
        "title": "지금 바로 시작하세요",
        "description": "RaymondsRisk로 숨겨진 투자 리스크를 발견하세요.",
    },
}


# 이미지 권장 사이즈 정의
IMAGE_SIZE_RECOMMENDATIONS = {
    "feature1.image": {"width": 640, "height": 360, "label": "기능1 이미지"},
    "feature2.image": {"width": 640, "height": 360, "label": "기능2 이미지"},
    "feature3.image": {"width": 640, "height": 360, "label": "기능3 이미지"},
    "feature4.image": {"width": 640, "height": 360, "label": "기능4 이미지"},
    "hero.image": {"width": 1200, "height": 600, "label": "히어로 배경 이미지"},
}
