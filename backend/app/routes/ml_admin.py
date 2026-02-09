"""
ML Admin Routes - ML 파이프라인 관리 API (관리자 전용)

모델 관리, 피처 모니터링, 학습 제어 등 ML 운영을 위한 엔드포인트.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import User
from app.routes.admin import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/ml", tags=["ML Admin"])


# =============================================================================
# Schemas
# =============================================================================

class ModelInfo(BaseModel):
    version: str
    type: str
    is_active: bool
    auc_roc: float
    precision_at_10: float
    recall: float
    brier_score: float
    training_date: date
    training_samples: int
    feature_count: int


class PredictionSummary(BaseModel):
    total_companies: int
    distribution: Dict[str, int]
    last_prediction_date: Optional[date]


class FeatureHealthSummary(BaseModel):
    total_features: int
    healthy: int
    warning: int
    critical: int
    avg_null_rate: float


class OverviewResponse(BaseModel):
    active_model: Optional[ModelInfo]
    prediction_summary: PredictionSummary
    feature_health: FeatureHealthSummary
    detection_rates: Dict[str, float]


class FeatureStat(BaseModel):
    name: str
    category: str
    null_count: int
    null_rate: float
    mean: Optional[float]
    std: Optional[float]
    min_val: Optional[float]
    max_val: Optional[float]
    health: str


class FeatureStatsResponse(BaseModel):
    total_records: int
    features: List[FeatureStat]


class DistributionBucket(BaseModel):
    range: str
    count: int
    pct: float


class RiskLevelStat(BaseModel):
    count: int
    pct: float
    avg_prob: float


class DistributionResponse(BaseModel):
    histogram: List[DistributionBucket]
    by_risk_level: Dict[str, RiskLevelStat]
    by_market: Dict[str, Dict[str, int]]


class DetectionStat(BaseModel):
    total: int
    by_risk_level: Dict[str, Dict[str, Any]]


class ValidationResponse(BaseModel):
    suspended_detection: DetectionStat
    managed_detection: DetectionStat


class ConfigResponse(BaseModel):
    model: Dict[str, Any]
    features: Dict[str, bool]
    risk_levels: Dict[str, List[float]]


class ConfigUpdateRequest(BaseModel):
    xgb_params: Optional[Dict[str, Any]] = None
    lgb_params: Optional[Dict[str, Any]] = None
    test_size: Optional[float] = None
    cv_folds: Optional[int] = None
    use_smote: Optional[bool] = None
    risk_levels: Optional[Dict[str, List[float]]] = None


class TrainRequest(BaseModel):
    version: str = "v3.0.0"
    run_batch_prediction: bool = True
    config_overrides: Optional[Dict[str, Any]] = None


class TrainStatusResponse(BaseModel):
    task_id: Optional[str]
    status: str
    phase: Optional[str]
    progress: int
    phases: List[Dict[str, Any]]
    started_at: Optional[datetime]
    elapsed_sec: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]


# =============================================================================
# Feature category mapping
# =============================================================================

FEATURE_CATEGORIES = {
    'exec_count': 'officer', 'exec_turnover_rate': 'officer',
    'exec_avg_tenure': 'officer', 'exec_other_company_count': 'officer',
    'exec_avg_other_companies': 'officer', 'exec_delisted_connection': 'officer',
    'exec_managed_connection': 'officer', 'exec_concurrent_positions': 'officer',
    'exec_network_density': 'officer', 'exec_high_risk_ratio': 'officer',
    'cb_count_1y': 'cb', 'cb_total_amount_1y': 'cb',
    'cb_subscriber_count': 'cb', 'cb_high_risk_subscriber_ratio': 'cb',
    'cb_subscriber_avg_investments': 'cb', 'cb_loss_company_connections': 'cb',
    'cb_delisted_connections': 'cb', 'cb_repeat_subscriber_ratio': 'cb',
    'largest_shareholder_ratio': 'shareholder', 'shareholder_change_1y': 'shareholder',
    'related_party_ratio': 'shareholder', 'shareholder_count': 'shareholder',
    'cei_score': 'index', 'cgi_score': 'index',
    'rii_score': 'index', 'mai_score': 'index',
}

FEATURE_NAMES = list(FEATURE_CATEGORIES.keys())


# =============================================================================
# 1. Overview
# =============================================================================

@router.get("/overview", response_model=OverviewResponse)
async def get_ml_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """ML 대시보드 요약"""

    # Active model
    model_row = (await db.execute(text("""
        SELECT model_version, model_type, auc_roc, precision_at_10,
               recall, brier_score, training_date, training_samples, feature_count
        FROM ml_models WHERE is_active = TRUE
        ORDER BY training_date DESC LIMIT 1
    """))).fetchone()

    active_model = None
    if model_row:
        active_model = ModelInfo(
            version=model_row.model_version,
            type=model_row.model_type,
            is_active=True,
            auc_roc=float(model_row.auc_roc),
            precision_at_10=float(model_row.precision_at_10),
            recall=float(model_row.recall),
            brier_score=float(model_row.brier_score),
            training_date=model_row.training_date,
            training_samples=model_row.training_samples,
            feature_count=model_row.feature_count,
        )

    # Prediction distribution
    dist_rows = (await db.execute(text(
        "SELECT risk_level, COUNT(*) as cnt FROM risk_predictions GROUP BY risk_level"
    ))).fetchall()
    dist = {r.risk_level: r.cnt for r in dist_rows}
    total_pred = sum(dist.values())

    last_date_row = (await db.execute(text(
        "SELECT MAX(prediction_date) FROM risk_predictions"
    ))).scalar()

    # Feature health
    feat_health = await _compute_feature_health(db)

    # Detection rates
    det = await _compute_detection_rates(db)

    return OverviewResponse(
        active_model=active_model,
        prediction_summary=PredictionSummary(
            total_companies=total_pred,
            distribution=dist,
            last_prediction_date=last_date_row,
        ),
        feature_health=feat_health,
        detection_rates=det,
    )


# =============================================================================
# 2. Models
# =============================================================================

@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """모델 버전 목록"""
    rows = (await db.execute(text("""
        SELECT model_version, model_type, is_active, auc_roc, precision_at_10,
               recall, brier_score, training_date, training_samples, feature_count
        FROM ml_models ORDER BY training_date DESC
    """))).fetchall()

    return [
        ModelInfo(
            version=r.model_version, type=r.model_type, is_active=r.is_active,
            auc_roc=float(r.auc_roc), precision_at_10=float(r.precision_at_10),
            recall=float(r.recall), brier_score=float(r.brier_score),
            training_date=r.training_date, training_samples=r.training_samples,
            feature_count=r.feature_count,
        )
        for r in rows
    ]


@router.post("/models/{version}/activate")
async def activate_model(
    version: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """활성 모델 변경"""
    # 대상 모델 존재 확인
    exists = (await db.execute(
        text("SELECT 1 FROM ml_models WHERE model_version = :v"),
        {'v': version}
    )).scalar()

    if not exists:
        raise HTTPException(404, f"모델 {version} 없음")

    # 전체 비활성화 후 대상 활성화
    await db.execute(text("UPDATE ml_models SET is_active = FALSE"))
    await db.execute(text(
        "UPDATE ml_models SET is_active = TRUE WHERE model_version = :v"
    ), {'v': version})
    await db.commit()

    return {"success": True, "activated_version": version}


# =============================================================================
# 3. Feature Stats
# =============================================================================

@router.get("/features/stats", response_model=FeatureStatsResponse)
async def get_feature_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """피처별 NULL/분포 통계"""

    total = (await db.execute(text("SELECT COUNT(*) FROM ml_features"))).scalar() or 0

    features = []
    for fname in FEATURE_NAMES:
        row = (await db.execute(text(f"""
            SELECT
                COUNT(*) - COUNT({fname}) as null_count,
                AVG({fname})::float as mean_val,
                STDDEV({fname})::float as std_val,
                MIN({fname})::float as min_val,
                MAX({fname})::float as max_val
            FROM ml_features
        """))).fetchone()

        null_count = row.null_count or 0
        null_rate = (null_count / total * 100) if total > 0 else 0

        health = "healthy"
        if null_rate > 50:
            health = "critical"
        elif null_rate > 10:
            health = "warning"

        features.append(FeatureStat(
            name=fname,
            category=FEATURE_CATEGORIES[fname],
            null_count=null_count,
            null_rate=round(null_rate, 1),
            mean=round(row.mean_val, 4) if row.mean_val is not None else None,
            std=round(row.std_val, 4) if row.std_val is not None else None,
            min_val=round(row.min_val, 4) if row.min_val is not None else None,
            max_val=round(row.max_val, 4) if row.max_val is not None else None,
            health=health,
        ))

    return FeatureStatsResponse(total_records=total, features=features)


# =============================================================================
# 4. Prediction Distribution
# =============================================================================

@router.get("/predictions/distribution", response_model=DistributionResponse)
async def get_prediction_distribution(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """예측 확률 분포"""

    total = (await db.execute(text("SELECT COUNT(*) FROM risk_predictions"))).scalar() or 1

    # Histogram (10% buckets)
    hist_rows = (await db.execute(text("""
        SELECT
            FLOOR(deterioration_probability * 10)::int as bucket,
            COUNT(*) as cnt
        FROM risk_predictions
        GROUP BY bucket
        ORDER BY bucket
    """))).fetchall()

    histogram = []
    for row in hist_rows:
        b = min(row.bucket, 9)
        lo = b / 10
        hi = (b + 1) / 10
        histogram.append(DistributionBucket(
            range=f"{lo:.1f}-{hi:.1f}",
            count=row.cnt,
            pct=round(row.cnt / total * 100, 1),
        ))

    # By risk level
    level_rows = (await db.execute(text("""
        SELECT risk_level, COUNT(*) as cnt,
               AVG(deterioration_probability)::float as avg_prob
        FROM risk_predictions
        GROUP BY risk_level
    """))).fetchall()

    by_level = {}
    for r in level_rows:
        by_level[r.risk_level] = RiskLevelStat(
            count=r.cnt,
            pct=round(r.cnt / total * 100, 1),
            avg_prob=round(r.avg_prob, 4),
        )

    # By market
    market_rows = (await db.execute(text("""
        SELECT c.market, rp.risk_level, COUNT(*) as cnt
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE c.market IS NOT NULL
        GROUP BY c.market, rp.risk_level
    """))).fetchall()

    by_market: Dict[str, Dict[str, int]] = {}
    for r in market_rows:
        if r.market not in by_market:
            by_market[r.market] = {}
        by_market[r.market][r.risk_level] = r.cnt

    return DistributionResponse(
        histogram=histogram,
        by_risk_level=by_level,
        by_market=by_market,
    )


# =============================================================================
# 5. Validation (Detection rates)
# =============================================================================

@router.get("/predictions/validation", response_model=ValidationResponse)
async def get_prediction_validation(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """거래정지/관리종목 탐지율"""

    susp = await _detection_by_status(db, "c.trading_status = 'SUSPENDED'")
    managed = await _detection_by_status(db, "c.is_managed = 'Y'")

    return ValidationResponse(
        suspended_detection=susp,
        managed_detection=managed,
    )


# =============================================================================
# 6. Config
# =============================================================================

@router.get("/config", response_model=ConfigResponse)
async def get_ml_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """하이퍼파라미터 조회"""

    # DB에서 override 조회
    overrides = {}
    try:
        rows = (await db.execute(text(
            "SELECT config_key, config_value FROM ml_config_overrides WHERE is_active = TRUE"
        ))).fetchall()
        for r in rows:
            overrides[r.config_key] = r.config_value
    except Exception:
        pass  # 테이블 미존재 시 기본값 사용

    # 기본 config + overrides 병합
    xgb_defaults = {
        'max_depth': 6, 'learning_rate': 0.1, 'n_estimators': 100,
        'subsample': 0.8, 'colsample_bytree': 0.8, 'scale_pos_weight': 8,
    }
    lgb_defaults = {
        'max_depth': 6, 'learning_rate': 0.1, 'n_estimators': 100,
        'subsample': 0.8, 'colsample_bytree': 0.8,
    }

    for key, val in overrides.items():
        if key.startswith('xgb_params.'):
            param = key.replace('xgb_params.', '')
            xgb_defaults[param] = val
        elif key.startswith('lgb_params.'):
            param = key.replace('lgb_params.', '')
            lgb_defaults[param] = val

    return ConfigResponse(
        model={
            "use_xgboost": True,
            "use_lightgbm": True,
            "use_catboost": False,
            "xgb_params": xgb_defaults,
            "lgb_params": lgb_defaults,
            "test_size": overrides.get('test_size', 0.2),
            "cv_folds": overrides.get('cv_folds', 5),
            "use_smote": overrides.get('use_smote', True),
        },
        features={
            "use_officer_features": True,
            "use_cb_features": True,
            "use_shareholder_features": True,
            "use_index_features": True,
        },
        risk_levels={
            "LOW": overrides.get('risk_levels.LOW', [0.0, 0.3]),
            "MEDIUM": overrides.get('risk_levels.MEDIUM', [0.3, 0.5]),
            "HIGH": overrides.get('risk_levels.HIGH', [0.5, 0.7]),
            "CRITICAL": overrides.get('risk_levels.CRITICAL', [0.7, 1.0]),
        },
    )


@router.put("/config")
async def update_ml_config(
    req: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """하이퍼파라미터 수정"""

    updated = []

    async def _upsert(key: str, value: Any):
        await db.execute(text("""
            INSERT INTO ml_config_overrides (id, config_key, config_value, is_active, updated_by, updated_at)
            VALUES (gen_random_uuid(), :key, :val::jsonb, TRUE, :user, NOW())
            ON CONFLICT (config_key) WHERE is_active = TRUE
            DO UPDATE SET config_value = :val::jsonb, updated_by = :user, updated_at = NOW()
        """), {'key': key, 'val': json.dumps(value), 'user': current_user.email})
        updated.append(key)

    if req.xgb_params:
        for k, v in req.xgb_params.items():
            await _upsert(f'xgb_params.{k}', v)

    if req.lgb_params:
        for k, v in req.lgb_params.items():
            await _upsert(f'lgb_params.{k}', v)

    if req.test_size is not None:
        await _upsert('test_size', req.test_size)
    if req.cv_folds is not None:
        await _upsert('cv_folds', req.cv_folds)
    if req.use_smote is not None:
        await _upsert('use_smote', req.use_smote)

    if req.risk_levels:
        for level, bounds in req.risk_levels.items():
            await _upsert(f'risk_levels.{level}', bounds)

    await db.commit()
    return {"success": True, "updated_params": updated}


# =============================================================================
# 7. Training
# =============================================================================

# In-memory training state (single server)
_training_state: Dict[str, Any] = {
    "task_id": None,
    "status": "idle",
    "phase": None,
    "progress": 0,
    "phases": [],
    "started_at": None,
    "result": None,
    "error": None,
    "process": None,
}


@router.post("/train")
async def start_training(
    req: TrainRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """학습 실행 트리거"""
    global _training_state

    if _training_state["status"] == "running":
        raise HTTPException(409, "학습이 이미 실행 중입니다.")

    # 버전 중복 확인
    exists = (await db.execute(
        text("SELECT 1 FROM ml_models WHERE model_version = :v"),
        {'v': req.version}
    )).scalar()
    if exists:
        raise HTTPException(409, f"모델 버전 {req.version}이 이미 존재합니다.")

    task_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    _training_state = {
        "task_id": task_id,
        "status": "running",
        "phase": "initializing",
        "progress": 0,
        "phases": [
            {"name": "data_loading", "status": "pending"},
            {"name": "model_training", "status": "pending"},
            {"name": "evaluation", "status": "pending"},
            {"name": "model_saving", "status": "pending"},
            {"name": "batch_prediction", "status": "pending" if req.run_batch_prediction else "skipped"},
        ],
        "started_at": datetime.now(),
        "result": None,
        "error": None,
        "process": None,
    }

    # 백그라운드 프로세스로 학습 실행
    db_url = os.environ.get('DATABASE_URL', '').replace('+asyncpg', '')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    venv_python = os.path.join(backend_dir, '.venv', 'bin', 'python3')
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    cmd = [venv_python, '-m', 'ml.training.trainer']
    env = {**os.environ, 'DATABASE_URL': db_url, 'PYTHONUNBUFFERED': '1'}

    try:
        proc = subprocess.Popen(
            cmd, cwd=backend_dir, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True,
        )
        _training_state["process"] = proc

        # 비동기로 프로세스 모니터링
        asyncio.get_event_loop().create_task(
            _monitor_training(proc, task_id, req.run_batch_prediction, backend_dir, env)
        )

    except Exception as e:
        _training_state["status"] = "failed"
        _training_state["error"] = str(e)
        raise HTTPException(500, f"학습 시작 실패: {e}")

    return {"task_id": task_id, "status": "started"}


@router.get("/train/status", response_model=TrainStatusResponse)
async def get_train_status(
    _: User = Depends(require_admin),
):
    """학습 진행 상황"""
    elapsed = None
    if _training_state["started_at"]:
        elapsed = int((datetime.now() - _training_state["started_at"]).total_seconds())

    return TrainStatusResponse(
        task_id=_training_state["task_id"],
        status=_training_state["status"],
        phase=_training_state["phase"],
        progress=_training_state["progress"],
        phases=_training_state["phases"],
        started_at=_training_state["started_at"],
        elapsed_sec=elapsed,
        result=_training_state["result"],
        error=_training_state["error"],
    )


# =============================================================================
# Helper functions
# =============================================================================

async def _monitor_training(proc, task_id, run_batch, backend_dir, env):
    """학습 프로세스 모니터링 (백그라운드 태스크)"""
    global _training_state

    try:
        # Phase: training
        _training_state["phase"] = "model_training"
        _training_state["progress"] = 20
        _training_state["phases"][0]["status"] = "completed"
        _training_state["phases"][1]["status"] = "in_progress"

        # stdout 읽기 (비동기 시뮬레이션)
        loop = asyncio.get_event_loop()
        returncode = await loop.run_in_executor(None, proc.wait)

        if returncode != 0:
            stdout = proc.stdout.read() if proc.stdout else ""
            _training_state["status"] = "failed"
            _training_state["error"] = f"학습 실패 (exit code {returncode}): {stdout[-500:]}"
            return

        _training_state["phases"][1]["status"] = "completed"
        _training_state["phases"][2]["status"] = "completed"
        _training_state["phases"][3]["status"] = "completed"
        _training_state["progress"] = 70

        # Batch prediction
        if run_batch:
            _training_state["phase"] = "batch_prediction"
            _training_state["phases"][4]["status"] = "in_progress"
            _training_state["progress"] = 80

            cmd2 = [env.get('PYTHON', sys.executable), '-m', 'ml.training.batch_predictor']
            proc2 = subprocess.Popen(
                cmd2, cwd=backend_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            returncode2 = await loop.run_in_executor(None, proc2.wait)

            if returncode2 == 0:
                _training_state["phases"][4]["status"] = "completed"
            else:
                _training_state["phases"][4]["status"] = "failed"

        _training_state["status"] = "completed"
        _training_state["phase"] = "done"
        _training_state["progress"] = 100

    except Exception as e:
        _training_state["status"] = "failed"
        _training_state["error"] = str(e)


async def _compute_feature_health(db: AsyncSession) -> FeatureHealthSummary:
    """피처 건강 상태 계산"""
    total = (await db.execute(text("SELECT COUNT(*) FROM ml_features"))).scalar() or 1

    healthy = warning = critical = 0
    null_rates = []

    for fname in FEATURE_NAMES:
        null_count = (await db.execute(
            text(f"SELECT COUNT(*) - COUNT({fname}) FROM ml_features")
        )).scalar() or 0
        rate = null_count / total * 100
        null_rates.append(rate)

        if rate > 50:
            critical += 1
        elif rate > 10:
            warning += 1
        else:
            healthy += 1

    return FeatureHealthSummary(
        total_features=len(FEATURE_NAMES),
        healthy=healthy,
        warning=warning,
        critical=critical,
        avg_null_rate=round(sum(null_rates) / len(null_rates), 1) if null_rates else 0,
    )


async def _compute_detection_rates(db: AsyncSession) -> Dict[str, float]:
    """탐지율 계산"""
    rates = {}

    # SUSPENDED → CRITICAL 비율
    susp_result = (await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN rp.risk_level = 'CRITICAL' THEN 1 END) as critical
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE c.trading_status = 'SUSPENDED'
    """))).fetchone()

    if susp_result and susp_result.total > 0:
        rates["suspended_critical"] = round(susp_result.critical / susp_result.total * 100, 1)
    else:
        rates["suspended_critical"] = 0

    # MANAGED → CRITICAL+HIGH 비율
    mgd_result = (await db.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN rp.risk_level IN ('CRITICAL', 'HIGH') THEN 1 END) as ch
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE c.is_managed = 'Y'
    """))).fetchone()

    if mgd_result and mgd_result.total > 0:
        rates["managed_critical_high"] = round(mgd_result.ch / mgd_result.total * 100, 1)
    else:
        rates["managed_critical_high"] = 0

    return rates


async def _detection_by_status(db: AsyncSession, where_clause: str) -> DetectionStat:
    """상태별 탐지 통계"""
    rows = (await db.execute(text(f"""
        SELECT rp.risk_level, COUNT(*) as cnt
        FROM risk_predictions rp
        JOIN companies c ON c.id = rp.company_id
        WHERE {where_clause}
        GROUP BY rp.risk_level
    """))).fetchall()

    total = sum(r.cnt for r in rows)
    by_level = {}
    for r in rows:
        by_level[r.risk_level] = {
            "count": r.cnt,
            "pct": round(r.cnt / total * 100, 1) if total > 0 else 0,
        }

    return DetectionStat(total=total, by_risk_level=by_level)
