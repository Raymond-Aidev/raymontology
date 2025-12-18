"""
Risk Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database import get_db
from app.schemas.risk import RiskScoreResponse
from app.services.risk_engine import RiskEngine

router = APIRouter(prefix="/api/companies", tags=["risk"])


@router.get("/{company_id}/risk-score", response_model=RiskScoreResponse)
async def get_company_risk_score(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    회사 리스크 점수 조회

    **Raymontology 핵심 기능**: 5가지 리스크 요소 분석

    ## 리스크 컴포넌트

    ### 1. 정보 비대칭 (Information Asymmetry) - 25%
    - CB 발행 빈도
    - 내부자 거래 패턴
    - 공시 지연/누락
    - 임원 네트워크 복잡도

    ### 2. 권력 집중 (Power Concentration) - 25%
    - 소유 집중도
    - 특수관계자 거래 비율
    - 사외이사 독립성
    - 순환 출자 구조

    ### 3. 거래 패턴 (Transaction Pattern) - 20%
    - 비정상 거래량
    - 주가 조작 의심
    - 공매도 급증
    - 대량 양수도

    ### 4. 펀드 리스크 (Fund Risk) - 15%
    - CB 보유 펀드 수
    - 특수관계 펀드 투자
    - 공동 투자 패턴
    - 펀드 간 담합 의심

    ### 5. 네트워크 리스크 (Network Risk) - 15%
    - 임원 겸직 수
    - 가족 관계망
    - 페이퍼컴퍼니 연결
    - 실질 지배자 은폐

    ## 리스크 레벨
    - **LOW** (0.0 ~ 0.4): 낮은 리스크
    - **MEDIUM** (0.4 ~ 0.6): 중간 리스크
    - **HIGH** (0.6 ~ 0.8): 높은 리스크
    - **CRITICAL** (0.8 ~ 1.0): 매우 높은 리스크 (⚠️ 투자 주의)

    ## 경로 파라미터
    - `company_id`: 회사 UUID

    ## 응답
    ```json
    {
      "company_id": "...",
      "company_name": "악덕주식회사",
      "total_score": 0.75,
      "risk_level": "HIGH",
      "components": {
        "information_asymmetry": {
          "score": 0.8,
          "factors": [
            {
              "name": "CB 발행 빈도",
              "value": 10,
              "score": 0.9,
              "weight": 0.4
            }
          ],
          "details": {...}
        },
        ...
      },
      "warnings": [
        "⚠️ CB 발행 빈도: 10 (위험 수준)"
      ],
      "calculated_at": "2024-01-15T10:30:00Z"
    }
    ```

    ## 예시
    ```
    GET /api/companies/550e8400-e29b-41d4-a716-446655440000/risk-score
    ```

    ## 에러
    - `404`: 회사를 찾을 수 없음
    - `500`: 리스크 계산 실패
    """
    try:
        # RiskEngine 생성
        engine = RiskEngine(db=db)

        # 리스크 점수 계산
        risk_score = await engine.calculate_risk_score(company_id)

        return risk_score

    except ValueError as e:
        # 회사를 찾을 수 없음
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        # 기타 에러
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate risk score: {str(e)}"
        )
