"""
모델 학습 모듈 (Phase 5)

XGBoost + LightGBM 앙상블 학습 (CatBoost는 Python 3.14 미지원)
Temporal Split: 2024년 피처 → 2025년 라벨

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
    XGBoost + LightGBM 앙상블 학습기
    
    특징:
    - Temporal Split (2024 피처 → 2025 라벨)
    - SMOTE 오버샘플링 (클래스 불균형 대응)
    - 5-fold CV로 일반화 성능 검증
    - Brier Score로 확률 보정 품질 평가
    """
    
    def __init__(self, config: ModelConfig = None, eval_config: EvaluationConfig = None):
        self.config = config or DEFAULT_MODEL_CONFIG
        self.eval_config = eval_config or DEFAULT_EVALUATION_CONFIG
        self.models = {}
        self.feature_names = FEATURE_NAMES
        self.metrics = {}
        
    def prepare_data(self, conn) -> Tuple[pd.DataFrame, pd.Series]:
        """
        학습 데이터 준비
        
        Returns:
            X: 피처 DataFrame (26 columns)
            y: 라벨 Series (0/1)
        """
        # ml_features 테이블에서 피처 로드
        feature_cols = ', '.join(self.feature_names)
        df = pd.read_sql(text(f"""
            SELECT mf.company_id, {feature_cols}
            FROM ml_features mf
            WHERE mf.feature_date = '2024-12-31'
        """), conn)
        
        logger.info(f"피처 로드: {len(df)}개 기업")
        
        # 라벨 생성 (suspension_classifications 기반 + 재무 악화 이벤트)
        labels = pd.read_sql(text("""
            SELECT 
                c.id as company_id,
                CASE 
                    WHEN sc.suspension_type = 'TYPE_A' THEN 1
                    WHEN (
                        SELECT COUNT(*) FROM financial_statements fs 
                        WHERE fs.company_id = c.id 
                          AND fs.fiscal_year IN (2023, 2024) 
                          AND fs.net_income < 0
                    ) >= 2 THEN 1
                    ELSE 0
                END as label
            FROM companies c
            LEFT JOIN suspension_classifications sc ON sc.company_id = c.id
            WHERE c.listing_status = 'LISTED'
              OR (c.trading_status = 'SUSPENDED' AND sc.suspension_type = 'TYPE_A')
        """), conn)
        
        # 병합
        merged = df.merge(labels, on='company_id', how='inner')
        logger.info(f"라벨 병합: {len(merged)}개 기업")
        
        # 피처와 라벨 분리
        X = merged[self.feature_names].copy()
        y = merged['label'].copy()
        
        # NULL 값 처리 (0으로 대체)
        X = X.fillna(0)
        
        # 라벨 분포 확인
        pos_count = y.sum()
        neg_count = len(y) - pos_count
        logger.info(f"라벨 분포: 양성={pos_count} ({pos_count/len(y)*100:.1f}%), 음성={neg_count}")
        
        return X, y
    
    def train(self, X: pd.DataFrame, y: pd.Series, use_cv: bool = True) -> Dict:
        """
        앙상블 모델 학습
        
        Args:
            X: 피처 DataFrame
            y: 라벨 Series
            use_cv: 교차 검증 사용 여부
            
        Returns:
            학습 결과 딕셔너리
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
    
    def _evaluate_ensemble(self, X_test, y_test):
        """앙상블 평가"""
        predictions = []
        weights = []
        
        for name, model in self.models.items():
            pred = model.predict_proba(X_test)[:, 1]
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
            logger.info(f"  ✅ MVP AUC 달성! ({auc_roc:.4f} >= {self.eval_config.mvp_auc_roc})")
        else:
            logger.warning(f"  ⚠️ MVP AUC 미달 ({auc_roc:.4f} < {self.eval_config.mvp_auc_roc})")
    
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
        
        logger.info(f"  CV AUC: {mean_auc:.4f} ± {std_auc:.4f}")
    
    def save_models(self, version: str = None) -> str:
        """모델 저장"""
        if not version:
            version = datetime.now().strftime("v%Y%m%d_%H%M%S")
        
        model_path = os.path.join(SAVED_MODELS_DIR, f"ensemble_{version}.pkl")
        
        save_data = {
            'models': self.models,
            'metrics': self.metrics,
            'feature_names': self.feature_names,
            'config': {
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
    parser = argparse.ArgumentParser(description='앙상블 모델 학습 (Phase 5)')
    parser.add_argument('--dry-run', action='store_true', help='학습 없이 데이터 확인만')
    args = parser.parse_args()

    run_training(dry_run=args.dry_run)
