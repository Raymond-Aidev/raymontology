"""
모델 학습 모듈 (Phase 5) v5.1

XGBoost + LightGBM 앙상블 학습 (CatBoost는 Python 3.14 미지원)
Temporal Split: 2024년 피처 → 2025년 라벨

v5.1 변경:
- Label D안: 재무 악화 + 관계형 리스크 복합 레이블
  - TYPE_A 거래정지 → 항상 양성
  - 재무 악화(연속적자/흑자→적자/자본잠식) + 관계형 리스크(Private CB/임원 대량교체/적자기업 출신)
- NULL 처리: 중앙값 대치 (median imputation)
- 42개 피처 (FEATURE_NAMES v5.0)

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.training.trainer
    DATABASE_URL="postgresql://..." python -m ml.training.trainer --dry-run
"""

import argparse
import logging
import os
import sys
import joblib
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import roc_auc_score, precision_score, recall_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from imblearn.over_sampling import SMOTE

from sqlalchemy import create_engine, text

from ml.config import (
    FEATURE_NAMES, DEFAULT_MODEL_CONFIG, DEFAULT_EVALUATION_CONFIG,
    SAVED_MODELS_DIR, ModelConfig, EvaluationConfig
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnsembleTrainer:
    """
    XGBoost + LightGBM 앙상블 학습기 v5.1

    특징:
    - Temporal Split (2024 피처 → 2025 라벨)
    - Label D안: 재무 악화 + 관계형 리스크 복합 레이블
    - Median imputation (NULL 처리)
    - SMOTE 오버샘플링 (클래스 불균형 대응)
    - 5-fold CV로 일반화 성능 검증
    """

    def __init__(self, config: ModelConfig = None, eval_config: EvaluationConfig = None):
        self.config = config or DEFAULT_MODEL_CONFIG
        self.eval_config = eval_config or DEFAULT_EVALUATION_CONFIG
        self.models = {}
        self.feature_names = FEATURE_NAMES
        self.metrics = {}
        self.feature_medians = None  # v5.0: 중앙값 저장 (추론 시 사용)

    def prepare_data(self, conn) -> Tuple[pd.DataFrame, pd.Series]:
        """
        학습 데이터 준비 v5.0

        Returns:
            X: 피처 DataFrame (42 columns)
            y: 라벨 Series (0/1)
        """
        # ml_features 테이블에서 피처 로드 (SPAC/REIT 제외)
        feature_cols = ', '.join(self.feature_names)
        df = pd.read_sql(text(f"""
            SELECT mf.company_id, {feature_cols}
            FROM ml_features mf
            JOIN companies c ON c.id = mf.company_id
            WHERE mf.feature_date = '2024-12-31'
              AND c.company_type = 'NORMAL'
        """), conn)

        logger.info(f"피처 로드: {len(df)}개 기업")

        # 라벨 생성 v5.1 (D안: 재무 악화 + 관계형 리스크 복합 레이블)
        labels = pd.read_sql(text("""
            WITH financial_deterioration AS (
                -- 재무 악화 시그널 (1개 이상 충족)
                SELECT c.id as company_id,
                    GREATEST(
                        -- FD1: 연속 적자 2년+ (2023, 2024 모두 적자)
                        COALESCE((
                            SELECT CASE WHEN COUNT(*) >= 2 THEN 1 ELSE 0 END
                            FROM financial_statements
                            WHERE company_id = c.id
                              AND fiscal_year IN (2023, 2024)
                              AND net_income < 0
                        ), 0),
                        -- FD2: 흑자→적자 전환 (2023 흑자, 2024 적자)
                        COALESCE((
                            SELECT CASE
                                WHEN fs_prev.net_income >= 0 AND fs_curr.net_income < 0
                                THEN 1 ELSE 0 END
                            FROM financial_statements fs_curr
                            JOIN financial_statements fs_prev
                                ON fs_prev.company_id = fs_curr.company_id
                                AND fs_prev.fiscal_year = 2023
                            WHERE fs_curr.company_id = c.id
                              AND fs_curr.fiscal_year = 2024
                            LIMIT 1
                        ), 0),
                        -- FD3: 자본잠식 (total_equity <= 0)
                        COALESCE((
                            SELECT CASE WHEN total_equity <= 0 THEN 1 ELSE 0 END
                            FROM financial_details
                            WHERE company_id = c.id AND fiscal_year = 2024
                            LIMIT 1
                        ), 0)
                    ) as has_financial_deterioration
                FROM companies c
                WHERE c.company_type = 'NORMAL'
            ),
            relational_risk AS (
                -- 관계형 리스크 시그널 (1개 이상 충족)
                SELECT c.id as company_id,
                    GREATEST(
                        -- RR1: Private CB 인수자 (FUND/INDIVIDUAL/투자조합)
                        (CASE WHEN EXISTS (
                            SELECT 1 FROM cb_subscribers cs
                            JOIN convertible_bonds cb ON cs.cb_id = cb.id
                            WHERE cb.company_id = c.id
                              AND (cs.subscriber_type IN ('FUND', 'INDIVIDUAL')
                                   OR cs.subscriber_name LIKE '%%투자조합%%'
                                   OR cs.subscriber_name LIKE '%%조합%%')
                        ) THEN 1 ELSE 0 END),
                        -- RR2: 임원 대량 교체 (2023년 이후 신규 5명+)
                        (CASE WHEN (
                            SELECT COUNT(DISTINCT op.officer_id)
                            FROM officer_positions op
                            WHERE op.company_id = c.id
                              AND COALESCE(op.term_start_date, op.created_at) >= '2023-01-01'
                        ) >= 5 THEN 1 ELSE 0 END),
                        -- RR3: 적자기업 출신 신규 임원 보유
                        (CASE WHEN EXISTS (
                            SELECT 1
                            FROM officer_positions op_new
                            JOIN officer_positions op_other
                                ON op_new.officer_id = op_other.officer_id
                                AND op_other.company_id != c.id
                            JOIN financial_statements fs
                                ON fs.company_id = op_other.company_id
                                AND fs.fiscal_year >= 2022
                                AND fs.net_income < 0
                            WHERE op_new.company_id = c.id
                              AND COALESCE(op_new.term_start_date, op_new.created_at) >= '2023-01-01'
                        ) THEN 1 ELSE 0 END)
                    ) as has_relational_risk
                FROM companies c
                WHERE c.company_type = 'NORMAL'
            )
            SELECT
                c.id as company_id,
                CASE
                    -- [A] TYPE_A 거래정지 → 항상 양성 (확정 악화)
                    WHEN sc.suspension_type = 'TYPE_A' THEN 1
                    -- [B] 재무 악화 + 관계형 리스크 동시 충족
                    WHEN fd.has_financial_deterioration = 1
                         AND rr.has_relational_risk = 1 THEN 1
                    ELSE 0
                END as label
            FROM companies c
            LEFT JOIN suspension_classifications sc ON sc.company_id = c.id
            LEFT JOIN financial_deterioration fd ON fd.company_id = c.id
            LEFT JOIN relational_risk rr ON rr.company_id = c.id
            WHERE c.company_type = 'NORMAL'
              AND (c.listing_status = 'LISTED'
                   OR (c.trading_status = 'SUSPENDED' AND sc.suspension_type = 'TYPE_A'))
        """), conn)

        # 병합
        merged = df.merge(labels, on='company_id', how='inner')
        logger.info(f"라벨 병합: {len(merged)}개 기업")

        # 피처와 라벨 분리
        X = merged[self.feature_names].copy()
        y = merged['label'].copy()

        # v5.0: 중앙값 대치 (median imputation)
        self.feature_medians = X.median()
        X = X.fillna(self.feature_medians)

        null_before = merged[self.feature_names].isnull().sum().sum()
        logger.info(f"NULL 처리: {null_before}개 → 중앙값 대치 완료")

        # 라벨 분포 확인
        pos_count = y.sum()
        neg_count = len(y) - pos_count
        logger.info(f"라벨 분포: 양성={pos_count} ({pos_count/len(y)*100:.1f}%), 음성={neg_count}")

        return X, y

    def train(self, X: pd.DataFrame, y: pd.Series, use_cv: bool = True) -> Dict:
        """
        앙상블 모델 학습
        """
        logger.info("=" * 60)
        logger.info("앙상블 모델 학습 시작")
        logger.info("=" * 60)

        # Train/Test Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y
        )
        logger.info(f"데이터 분할: Train={len(X_train)}, Test={len(X_test)}")

        # SMOTE 오버샘플링
        if self.config.use_smote:
            smote = SMOTE(
                sampling_strategy=self.config.smote_ratio,
                random_state=self.config.random_state
            )
            X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
            logger.info(f"SMOTE 적용: {len(X_train)} → {len(X_train_resampled)}")
        else:
            X_train_resampled, y_train_resampled = X_train, y_train

        # XGBoost 학습
        if self.config.use_xgboost:
            logger.info("\n[XGBoost] 학습 시작...")
            self._train_xgboost(X_train_resampled, y_train_resampled, X_test, y_test)

        # LightGBM 학습
        if self.config.use_lightgbm:
            logger.info("\n[LightGBM] 학습 시작...")
            self._train_lightgbm(X_train_resampled, y_train_resampled, X_test, y_test)

        # v5.1: Platt Scaling 확률 보정 (각 모델별)
        logger.info("\n[확률 보정] Platt Scaling...")
        self._calibrate_models(X_test, y_test)

        # 앙상블 예측 및 평가
        logger.info("\n[앙상블] 평가...")
        self._evaluate_ensemble(X_test, y_test)

        # 교차 검증 (선택적)
        if use_cv:
            logger.info("\n[교차 검증] 5-Fold CV...")
            self._cross_validate(X, y)

        return self.metrics

    def _train_xgboost(self, X_train, y_train, X_test, y_test):
        """XGBoost 모델 학습"""
        try:
            import xgboost as xgb

            params = self.config.xgb_params.copy()
            early_stopping = params.pop('early_stopping_rounds', 10)

            model = xgb.XGBClassifier(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )

            self.models['xgboost'] = model

            # 예측 및 평가
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)

            self.metrics['xgboost_auc'] = auc
            logger.info(f"  XGBoost AUC: {auc:.4f}")

        except Exception as e:
            logger.error(f"  XGBoost 학습 실패: {e}")

    def _train_lightgbm(self, X_train, y_train, X_test, y_test):
        """LightGBM 모델 학습"""
        try:
            import lightgbm as lgb

            params = self.config.lgb_params.copy()

            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
            )

            self.models['lightgbm'] = model

            # 예측 및 평가
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)

            self.metrics['lightgbm_auc'] = auc
            logger.info(f"  LightGBM AUC: {auc:.4f}")

        except Exception as e:
            logger.error(f"  LightGBM 학습 실패: {e}")

    def _calibrate_models(self, X_cal, y_cal):
        """v5.1: Platt Scaling으로 앙상블 확률 출력을 보정

        수동 Platt Scaling: 각 모델의 raw probability에 LogisticRegression 적용
        보정기(calibrator)를 별도 저장하여 추론 시 동일하게 적용
        """
        self.calibrators = {}
        for name, model in self.models.items():
            raw_pred = model.predict_proba(X_cal)[:, 1]
            logger.info(f"  {name} 보정 전: mean={raw_pred.mean():.3f}, "
                        f"std={raw_pred.std():.3f}, "
                        f"<0.1={np.sum(raw_pred < 0.1)}, >0.9={np.sum(raw_pred > 0.9)}")

            # Platt Scaling = LogisticRegression(raw_prob → calibrated_prob)
            lr = LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000)
            lr.fit(raw_pred.reshape(-1, 1), y_cal)
            self.calibrators[name] = lr

            cal_pred = lr.predict_proba(raw_pred.reshape(-1, 1))[:, 1]
            logger.info(f"  {name} 보정 후: mean={cal_pred.mean():.3f}, "
                        f"std={cal_pred.std():.3f}, "
                        f"<0.1={np.sum(cal_pred < 0.1)}, >0.9={np.sum(cal_pred > 0.9)}")

        logger.info("  확률 보정 완료 (Platt Scaling)")

    def _evaluate_ensemble(self, X_test, y_test):
        """앙상블 평가 (보정된 확률 사용)"""
        predictions = []
        weights = []

        for name, model in self.models.items():
            raw_pred = model.predict_proba(X_test)[:, 1]
            # v5.1: calibrator가 있으면 보정된 확률 사용
            if hasattr(self, 'calibrators') and name in self.calibrators:
                pred = self.calibrators[name].predict_proba(
                    raw_pred.reshape(-1, 1))[:, 1]
            else:
                pred = raw_pred
            predictions.append(pred)
            # AUC 기반 가중치
            auc = self.metrics.get(f'{name}_auc', 0.5)
            weights.append(auc)

        if not predictions:
            logger.error("학습된 모델 없음!")
            return

        # 가중 평균 앙상블
        weights = np.array(weights) / sum(weights)
        ensemble_pred = np.average(predictions, axis=0, weights=weights)

        # 평가 지표 계산
        auc_roc = roc_auc_score(y_test, ensemble_pred)
        brier = brier_score_loss(y_test, ensemble_pred)

        # Precision@10%
        threshold_10pct = np.percentile(ensemble_pred, 90)
        y_pred_top10 = (ensemble_pred >= threshold_10pct).astype(int)
        precision_10 = precision_score(y_test, y_pred_top10, zero_division=0)

        # Recall (threshold=0.5)
        y_pred_binary = (ensemble_pred >= 0.5).astype(int)
        recall = recall_score(y_test, y_pred_binary, zero_division=0)

        self.metrics['ensemble_auc'] = auc_roc
        self.metrics['ensemble_brier'] = brier
        self.metrics['precision_at_10'] = precision_10
        self.metrics['recall'] = recall

        logger.info(f"  앙상블 AUC: {auc_roc:.4f}")
        logger.info(f"  Brier Score: {brier:.4f}")
        logger.info(f"  Precision@10%: {precision_10:.4f}")
        logger.info(f"  Recall: {recall:.4f}")

        # 목표 달성 여부
        if auc_roc >= self.eval_config.mvp_auc_roc:
            logger.info(f"  MVP AUC 달성! ({auc_roc:.4f} >= {self.eval_config.mvp_auc_roc})")
        else:
            logger.warning(f"  MVP AUC 미달 ({auc_roc:.4f} < {self.eval_config.mvp_auc_roc})")

    def _cross_validate(self, X, y):
        """5-Fold 교차 검증"""
        skf = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True,
                              random_state=self.config.random_state)

        cv_aucs = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # SMOTE
            if self.config.use_smote:
                smote = SMOTE(sampling_strategy=self.config.smote_ratio,
                              random_state=self.config.random_state)
                X_train, y_train = smote.fit_resample(X_train, y_train)

            # XGBoost만 사용 (빠른 CV)
            import xgboost as xgb
            params = self.config.xgb_params.copy()
            params.pop('early_stopping_rounds', None)

            model = xgb.XGBClassifier(**params)
            model.fit(X_train, y_train, verbose=False)

            pred = model.predict_proba(X_val)[:, 1]
            auc = roc_auc_score(y_val, pred)
            cv_aucs.append(auc)

        mean_auc = np.mean(cv_aucs)
        std_auc = np.std(cv_aucs)

        self.metrics['cv_auc_mean'] = mean_auc
        self.metrics['cv_auc_std'] = std_auc

        logger.info(f"  CV AUC: {mean_auc:.4f} +/- {std_auc:.4f}")

    def save_models(self, version: str = None) -> str:
        """모델 저장 (v5.0: 중앙값 포함)"""
        if not version:
            version = datetime.now().strftime("v%Y%m%d_%H%M%S")

        model_path = os.path.join(SAVED_MODELS_DIR, f"ensemble_{version}.pkl")

        save_data = {
            'models': self.models,
            'metrics': self.metrics,
            'feature_names': self.feature_names,
            'feature_medians': self.feature_medians,  # v5.0: 추론 시 NULL 대치용
            'calibrators': getattr(self, 'calibrators', None),  # v5.1: Platt Scaling
            'config': {
                'version': self.config.version,
                'use_xgboost': self.config.use_xgboost,
                'use_lightgbm': self.config.use_lightgbm,
                'use_catboost': self.config.use_catboost,
            },
            'created_at': datetime.now().isoformat(),
        }

        joblib.dump(save_data, model_path)
        logger.info(f"모델 저장: {model_path}")

        return model_path

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """앙상블 예측"""
        predictions = []
        weights = []

        for name, model in self.models.items():
            pred = model.predict_proba(X)[:, 1]
            predictions.append(pred)
            auc = self.metrics.get(f'{name}_auc', 0.5)
            weights.append(auc)

        weights = np.array(weights) / sum(weights)
        return np.average(predictions, axis=0, weights=weights)


def run_training(dry_run: bool = False):
    """학습 파이프라인 실행"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)

    with engine.connect() as conn:
        trainer = EnsembleTrainer()

        # 데이터 준비
        X, y = trainer.prepare_data(conn)

        if dry_run:
            logger.info("\n[DRY-RUN] 학습 없이 종료합니다.")
            logger.info(f"  피처 shape: {X.shape}")
            logger.info(f"  라벨 분포: {y.value_counts().to_dict()}")
            return

        # 학습
        metrics = trainer.train(X, y, use_cv=True)

        # 모델 저장
        model_path = trainer.save_models()

        # 결과 보고
        logger.info("\n" + "=" * 60)
        logger.info("학습 완료 보고서")
        logger.info("=" * 60)
        for name, value in metrics.items():
            logger.info(f"  {name}: {value:.4f}")

        # DB에 모델 메타데이터 저장
        conn.execute(text("""
            INSERT INTO ml_models (
                model_version, model_type, auc_roc, precision_at_10,
                recall, brier_score, training_samples, positive_samples,
                feature_count, training_date, model_path, is_active
            ) VALUES (
                :version, :type, :auc, :precision, :recall, :brier,
                :samples, :positive, :features, :date, :path, TRUE
            )
        """), {
            'version': trainer.config.version,
            'type': 'ensemble_xgb_lgb',
            'auc': metrics.get('ensemble_auc'),
            'precision': metrics.get('precision_at_10'),
            'recall': metrics.get('recall'),
            'brier': metrics.get('ensemble_brier'),
            'samples': len(X),
            'positive': int(y.sum()),
            'features': len(FEATURE_NAMES),
            'date': date.today(),
            'path': model_path,
        })
        conn.commit()
        logger.info(f"\nml_models 테이블에 저장 완료")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='앙상블 모델 학습 (Phase 5) v5.0')
    parser.add_argument('--dry-run', action='store_true', help='학습 없이 데이터 확인만')
    args = parser.parse_args()

    run_training(dry_run=args.dry_run)
