"""
ML Pipeline 설정 v2.0

피처, 모델, 평가 관련 설정값 정의
- CatBoost: Python 3.14 미지원으로 비활성화 (XGBoost + LightGBM 2-model 앙상블)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os


# =============================================================================
# 피처 설정
# =============================================================================

FEATURE_NAMES = [
    # 임원 네트워크 (E01-E10)
    'exec_count', 'exec_turnover_rate', 'exec_avg_tenure',
    'exec_other_company_count', 'exec_avg_other_companies',
    'exec_delisted_connection', 'exec_managed_connection',
    'exec_concurrent_positions', 'exec_network_density', 'exec_high_risk_ratio',
    # CB 투자자 (C01-C08)
    'cb_count_1y', 'cb_total_amount_1y', 'cb_subscriber_count',
    'cb_high_risk_subscriber_ratio', 'cb_subscriber_avg_investments',
    'cb_loss_company_connections', 'cb_delisted_connections', 'cb_repeat_subscriber_ratio',
    # 대주주 (S01-S04)
    'largest_shareholder_ratio', 'shareholder_change_1y',
    'related_party_ratio', 'shareholder_count',
    # 4대 인덱스 (I01-I04)
    'cei_score', 'cgi_score', 'rii_score', 'mai_score',
]


@dataclass
class FeatureConfig:
    """피처 엔지니어링 설정"""

    # 피처 그룹 활성화
    use_officer_features: bool = True     # 임원 네트워크 (10개)
    use_cb_features: bool = True          # CB 투자자 (8개)
    use_shareholder_features: bool = True  # 대주주 (4개)
    use_index_features: bool = True       # 4대 인덱스 (4개)

    # 임원 네트워크 피처 임계값
    multi_company_threshold: int = 2      # 겸직 기준 (N개사 이상)
    high_risk_career_threshold: int = 5   # 고위험 경력 기준 (5개사+)
    deficit_lookback_years: int = 2       # 적자기업 판정 기간

    # CB 피처 임계값
    high_risk_subscriber_loss_ratio: float = 0.5  # 적자기업 투자비율 50%+

    # 시계열 설정
    lookback_years: int = 3               # 피처 계산 기간
    feature_date_year: int = 2024         # 피처 기준 연도 (Temporal Split X)


# =============================================================================
# 라벨 설정
# =============================================================================

@dataclass
class LabelConfig:
    """라벨 생성 설정"""

    # 예측 기간
    lookforward_months: int = 12

    # 악화 이벤트 가중치 (v2.0: DB 검증 반영)
    event_weights: Dict[str, float] = field(default_factory=lambda: {
        'suspension_type_a': 1.0,     # 거래정지 (재무악화) - 최고 수준
        'index_drop': 0.4,            # 인덱스 20% 이상 하락
        'consecutive_loss': 0.3,      # 연속 적자 (2년+)
        # 비활성화된 라벨 (데이터 부재)
        # 'managed': 0.6,             # 관리종목 (is_managed 전부 'N')
        # 'delisting': 1.0,           # 상장폐지 (774건 삭제됨)
    })

    # 인덱스 급락 임계값
    index_drop_threshold: float = 0.2  # 20%

    # 연속 적자 기준
    consecutive_loss_years: int = 2

    # Temporal Split 연도
    feature_year: int = 2024      # 피처 기준 연도
    label_year: int = 2025        # 라벨 기준 연도


# =============================================================================
# 모델 설정
# =============================================================================

@dataclass
class ModelConfig:
    """모델 학습 설정"""

    # 모델 버전
    version: str = "v1.0.0"

    # 앙상블 구성 (CatBoost는 Python 3.14 미지원으로 비활성화)
    use_xgboost: bool = True
    use_lightgbm: bool = True
    use_catboost: bool = False

    # XGBoost 하이퍼파라미터
    xgb_params: Dict = field(default_factory=lambda: {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'early_stopping_rounds': 10,
        'scale_pos_weight': 8,      # v2.0: 클래스 불균형 대응 (~8.3% 양성)
        'random_state': 42,
    })

    # LightGBM 하이퍼파라미터
    lgb_params: Dict = field(default_factory=lambda: {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'objective': 'binary',
        'metric': 'auc',
        'is_unbalance': True,       # v2.0: 클래스 불균형 대응
        'random_state': 42,
        'verbose': -1,
    })

    # 학습 설정
    test_size: float = 0.2
    cv_folds: int = 5
    random_state: int = 42

    # 클래스 불균형 처리
    use_smote: bool = True
    smote_ratio: float = 0.5


# =============================================================================
# 평가 설정
# =============================================================================

@dataclass
class EvaluationConfig:
    """평가 지표 설정"""

    # 목표 지표
    target_auc_roc: float = 0.75
    target_precision_at_10: float = 0.50
    target_recall: float = 0.70
    target_brier_score: float = 0.15

    # MVP 기준 (최소 요구사항)
    mvp_auc_roc: float = 0.70
    mvp_precision_at_10: float = 0.40
    mvp_recall: float = 0.60

    # Phase 6b: 거래정지 기업 검증 합격 기준
    min_detection_rate_at_50pct: float = 0.50   # TYPE_A 50%+에서 예측값 ≥ 0.50
    min_detection_rate_at_30pct: float = 0.70   # TYPE_A 70%+에서 예측값 ≥ 0.30
    max_false_negative_rate: float = 0.30       # 미탐지 30% 이하


# =============================================================================
# 위험 단계 정의
# =============================================================================

RISK_LEVELS = {
    'LOW': (0.0, 0.3),       # 0-30%
    'MEDIUM': (0.3, 0.5),    # 30-50%
    'HIGH': (0.5, 0.7),      # 50-70%
    'CRITICAL': (0.7, 1.0),  # 70-100%
}

RISK_COLORS = {
    'LOW': '#22C55E',        # 초록
    'MEDIUM': '#F59E0B',     # 주황
    'HIGH': '#EF4444',       # 빨강
    'CRITICAL': '#7C2D12',   # 진한 빨강
}


def get_risk_level(probability: float) -> str:
    """확률값을 위험 단계로 변환"""
    if probability >= 0.70:
        return 'CRITICAL'
    if probability >= 0.50:
        return 'HIGH'
    if probability >= 0.30:
        return 'MEDIUM'
    return 'LOW'


# =============================================================================
# 경로 설정
# =============================================================================

ML_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_DIR = os.path.join(ML_DIR, 'saved_models')
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)


# =============================================================================
# DB 연결 (로컬 학습용 - 동기식)
# =============================================================================

def get_sync_db_url() -> str:
    """로컬 학습용 동기 DB URL 반환"""
    url = os.environ.get('DATABASE_URL', '')
    # async URL을 sync로 변환
    if 'asyncpg' in url:
        url = url.replace('+asyncpg', '')
    # postgres:// → postgresql://
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


# =============================================================================
# 기본 설정 인스턴스
# =============================================================================

DEFAULT_FEATURE_CONFIG = FeatureConfig()
DEFAULT_LABEL_CONFIG = LabelConfig()
DEFAULT_MODEL_CONFIG = ModelConfig()
DEFAULT_EVALUATION_CONFIG = EvaluationConfig()
