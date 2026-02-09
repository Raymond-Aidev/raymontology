"""
평가 모듈 (Phase 6a + 6b)

정량 평가 및 거래정지 기업 검증

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.training.evaluator --model-path path/to/model.pkl
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, 
    brier_score_loss, confusion_matrix, classification_report
)
from sqlalchemy import create_engine, text

from ml.config import (
    FEATURE_NAMES, SAVED_MODELS_DIR, DEFAULT_EVALUATION_CONFIG,
    EvaluationConfig, get_risk_level
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """모델 평가기 (Phase 6a + 6b)"""
    
    def __init__(self, conn, model_path: str = None, config: EvaluationConfig = None):
        self.conn = conn
        self.config = config or DEFAULT_EVALUATION_CONFIG
        self.model_data = None
        self.models = {}
        
        if model_path:
            self._load_model(model_path)
        else:
            self._load_latest_model()
    
    def _load_model(self, path: str):
        """모델 로드"""
        self.model_data = joblib.load(path)
        self.models = self.model_data['models']
        logger.info(f"모델 로드: {path}")
    
    def _load_latest_model(self):
        """최신 모델 로드"""
        model_files = sorted([
            f for f in os.listdir(SAVED_MODELS_DIR)
            if f.startswith('ensemble_') and f.endswith('.pkl')
        ], reverse=True)
        
        if model_files:
            self._load_model(os.path.join(SAVED_MODELS_DIR, model_files[0]))
        else:
            raise FileNotFoundError("학습된 모델이 없습니다.")
    
    def evaluate_quantitative(self) -> Dict:
        """
        Phase 6a: 정량 평가
        
        Returns:
            평가 지표 딕셔너리
        """
        logger.info("=" * 60)
        logger.info("Phase 6a: 정량 평가")
        logger.info("=" * 60)
        
        # 테스트 데이터 로드
        feature_cols = ', '.join(FEATURE_NAMES)
        df = pd.read_sql(text(f"""
            SELECT 
                mf.company_id, 
                {feature_cols},
                CASE 
                    WHEN sc.suspension_type = 'TYPE_A' THEN 1
                    WHEN (
                        SELECT COUNT(*) FROM financial_statements fs 
                        WHERE fs.company_id = mf.company_id 
                          AND fs.fiscal_year IN (2023, 2024) 
                          AND fs.net_income < 0
                    ) >= 2 THEN 1
                    ELSE 0
                END as label
            FROM ml_features mf
            LEFT JOIN suspension_classifications sc ON sc.company_id = mf.company_id
            WHERE mf.feature_date = '2024-12-31'
        """), self.conn)
        
        X = df[FEATURE_NAMES].fillna(0)
        y = df['label']
        
        # 앙상블 예측
        predictions = []
        weights = []
        metrics = self.model_data.get('metrics', {})
        
        for name, model in self.models.items():
            pred = model.predict_proba(X)[:, 1]
            predictions.append(pred)
            auc = metrics.get(f'{name}_auc', 0.5)
            weights.append(auc)
        
        weights = np.array(weights) / sum(weights)
        y_pred_proba = np.average(predictions, axis=0, weights=weights)
        y_pred_binary = (y_pred_proba >= 0.5).astype(int)
        
        # 평가 지표 계산
        results = {}
        
        results['auc_roc'] = roc_auc_score(y, y_pred_proba)
        results['brier_score'] = brier_score_loss(y, y_pred_proba)
        results['recall'] = recall_score(y, y_pred_binary, zero_division=0)
        
        # Precision@10%
        threshold_10pct = np.percentile(y_pred_proba, 90)
        y_pred_top10 = (y_pred_proba >= threshold_10pct).astype(int)
        results['precision_at_10'] = precision_score(y, y_pred_top10, zero_division=0)
        
        # 혼동 행렬
        cm = confusion_matrix(y, y_pred_binary)
        results['confusion_matrix'] = cm.tolist()
        
        # 목표 달성 여부
        logger.info("\n평가 결과:")
        for name, value in results.items():
            if name != 'confusion_matrix':
                logger.info(f"  {name}: {value:.4f}")
        
        logger.info(f"\n혼동 행렬:\n{cm}")
        
        # MVP 기준 체크
        if results['auc_roc'] >= self.config.mvp_auc_roc:
            logger.info(f"\n✅ MVP AUC 달성! ({results['auc_roc']:.4f} >= {self.config.mvp_auc_roc})")
        else:
            logger.warning(f"\n⚠️ MVP AUC 미달 ({results['auc_roc']:.4f} < {self.config.mvp_auc_roc})")
        
        return results
    
    def evaluate_suspended_companies(self) -> Dict:
        """
        Phase 6b: 거래정지 기업 검증
        
        TYPE_A 기업들의 예측값이 높은지 확인
        
        Returns:
            검증 결과 딕셔너리
        """
        logger.info("\n" + "=" * 60)
        logger.info("Phase 6b: 거래정지 기업 검증")
        logger.info("=" * 60)
        
        # TYPE_A 기업 피처 로드
        feature_cols = ', '.join(FEATURE_NAMES)
        df = pd.read_sql(text(f"""
            SELECT 
                mf.company_id,
                c.name,
                c.ticker,
                {feature_cols}
            FROM ml_features mf
            JOIN suspension_classifications sc ON sc.company_id = mf.company_id
            JOIN companies c ON c.id = mf.company_id
            WHERE sc.suspension_type = 'TYPE_A'
              AND mf.feature_date = '2024-12-31'
        """), self.conn)
        
        if len(df) == 0:
            logger.warning("TYPE_A 기업 피처 데이터 없음")
            return {}
        
        X = df[FEATURE_NAMES].fillna(0)
        
        # 앙상블 예측
        predictions = []
        weights = []
        metrics = self.model_data.get('metrics', {})
        
        for name, model in self.models.items():
            pred = model.predict_proba(X)[:, 1]
            predictions.append(pred)
            auc = metrics.get(f'{name}_auc', 0.5)
            weights.append(auc)
        
        weights = np.array(weights) / sum(weights)
        y_pred_proba = np.average(predictions, axis=0, weights=weights)
        
        # 분석
        df['pred_prob'] = y_pred_proba
        df['risk_level'] = [get_risk_level(p) for p in y_pred_proba]
        
        total = len(df)
        
        # 임계값별 탐지율
        detection_at_50 = (y_pred_proba >= 0.5).sum() / total
        detection_at_30 = (y_pred_proba >= 0.3).sum() / total
        detection_at_70 = (y_pred_proba >= 0.7).sum() / total
        
        results = {
            'total_type_a': total,
            'detection_at_50pct': detection_at_50,
            'detection_at_30pct': detection_at_30,
            'detection_at_70pct': detection_at_70,
            'mean_prob': float(y_pred_proba.mean()),
            'median_prob': float(np.median(y_pred_proba)),
            'min_prob': float(y_pred_proba.min()),
            'max_prob': float(y_pred_proba.max()),
        }
        
        # 위험 등급 분포
        level_dist = df['risk_level'].value_counts().to_dict()
        results['level_distribution'] = level_dist
        
        logger.info(f"\nTYPE_A 기업 수: {total}개")
        logger.info(f"\n예측값 통계:")
        logger.info(f"  평균: {results['mean_prob']:.4f}")
        logger.info(f"  중앙값: {results['median_prob']:.4f}")
        logger.info(f"  최소/최대: {results['min_prob']:.4f} / {results['max_prob']:.4f}")
        
        logger.info(f"\n임계값별 탐지율:")
        logger.info(f"  >= 0.30: {detection_at_30*100:.1f}%")
        logger.info(f"  >= 0.50: {detection_at_50*100:.1f}%")
        logger.info(f"  >= 0.70: {detection_at_70*100:.1f}%")
        
        logger.info(f"\n위험 등급 분포:")
        for level, count in level_dist.items():
            pct = count / total * 100
            logger.info(f"  {level}: {count}개 ({pct:.1f}%)")
        
        # 합격 기준 체크
        if detection_at_50 >= self.config.min_detection_rate_at_50pct:
            logger.info(f"\n✅ 50% 임계값 탐지율 합격! ({detection_at_50*100:.1f}% >= {self.config.min_detection_rate_at_50pct*100}%)")
        else:
            logger.warning(f"\n⚠️ 50% 임계값 탐지율 미달 ({detection_at_50*100:.1f}% < {self.config.min_detection_rate_at_50pct*100}%)")
        
        # 미탐지 기업 TOP 10
        false_negatives = df[df['pred_prob'] < 0.3].sort_values('pred_prob').head(10)
        if len(false_negatives) > 0:
            logger.info(f"\n⚠️ 미탐지 기업 (예측값 < 0.30):")
            for _, row in false_negatives.iterrows():
                logger.info(f"  {row['name']} ({row['ticker']}): {row['pred_prob']:.4f}")
        
        return results


def run_evaluation(model_path: str = None):
    """평가 파이프라인 실행"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)
    
    with engine.connect() as conn:
        evaluator = ModelEvaluator(conn, model_path=model_path)
        
        # Phase 6a: 정량 평가
        quant_results = evaluator.evaluate_quantitative()
        
        # Phase 6b: 거래정지 기업 검증
        suspended_results = evaluator.evaluate_suspended_companies()
        
        # 종합 보고서
        logger.info("\n" + "=" * 60)
        logger.info("종합 평가 보고서")
        logger.info("=" * 60)
        
        all_passed = True
        
        # MVP 기준 체크
        if quant_results.get('auc_roc', 0) >= DEFAULT_EVALUATION_CONFIG.mvp_auc_roc:
            logger.info("✅ AUC-ROC: 합격")
        else:
            logger.info("❌ AUC-ROC: 불합격")
            all_passed = False
        
        if suspended_results.get('detection_at_50pct', 0) >= DEFAULT_EVALUATION_CONFIG.min_detection_rate_at_50pct:
            logger.info("✅ TYPE_A 탐지율 (50%): 합격")
        else:
            logger.info("❌ TYPE_A 탐지율 (50%): 불합격")
            all_passed = False
        
        if all_passed:
            logger.info("\n🎉 모든 평가 기준 통과! 프로덕션 배포 가능")
        else:
            logger.info("\n⚠️ 일부 평가 기준 미달. 모델 개선 필요")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='모델 평가 (Phase 6)')
    parser.add_argument('--model-path', type=str, help='모델 파일 경로')
    args = parser.parse_args()

    run_evaluation(model_path=args.model_path)
