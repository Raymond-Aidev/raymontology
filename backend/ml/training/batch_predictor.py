"""
배치 추론 모듈 (Phase 7)

전체 기업 대상 악화 확률 예측 및 risk_predictions 테이블 저장

Usage:
    cd backend
    DATABASE_URL="postgresql://..." python -m ml.training.batch_predictor
    DATABASE_URL="postgresql://..." python -m ml.training.batch_predictor --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import joblib

from sqlalchemy import create_engine, text

from ml.config import FEATURE_NAMES, SAVED_MODELS_DIR, get_risk_level

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BatchPredictor:
    """전체 기업 대상 악화 확률 예측"""
    
    def __init__(self, conn, model_path: str = None):
        self.conn = conn
        self.model_data = None
        self.models = {}
        self.metrics = {}
        
        # 최신 모델 로드
        if model_path:
            self._load_model(model_path)
        else:
            self._load_latest_model()
    
    def _load_model(self, path: str):
        """모델 로드"""
        self.model_data = joblib.load(path)
        self.models = self.model_data['models']
        self.metrics = self.model_data['metrics']
        logger.info(f"모델 로드: {path}")
    
    def _load_latest_model(self):
        """최신 모델 로드"""
        # DB에서 활성 모델 경로 조회
        result = self.conn.execute(text("""
            SELECT model_path FROM ml_models
            WHERE is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)).fetchone()
        
        if result and result.model_path:
            self._load_model(result.model_path)
        else:
            # 파일 시스템에서 최신 모델 찾기
            model_files = sorted([
                f for f in os.listdir(SAVED_MODELS_DIR)
                if f.startswith('ensemble_') and f.endswith('.pkl')
            ], reverse=True)
            
            if model_files:
                self._load_model(os.path.join(SAVED_MODELS_DIR, model_files[0]))
            else:
                raise FileNotFoundError("학습된 모델이 없습니다. 먼저 학습을 실행하세요.")
    
    def predict_all(self, dry_run: bool = False) -> Dict:
        """전체 기업 예측"""
        # 피처 로드
        feature_cols = ', '.join(FEATURE_NAMES)
        df = pd.read_sql(text(f"""
            SELECT mf.company_id, {feature_cols}
            FROM ml_features mf
            WHERE mf.feature_date = '2024-12-31'
        """), self.conn)
        
        logger.info(f"예측 대상: {len(df)}개 기업")
        
        if len(df) == 0:
            logger.warning("피처 데이터가 없습니다.")
            return {}
        
        # 피처 추출
        X = df[FEATURE_NAMES].fillna(0)
        company_ids = df['company_id'].tolist()
        
        # 앙상블 예측
        predictions = []
        weights = []
        
        for name, model in self.models.items():
            pred = model.predict_proba(X)[:, 1]
            predictions.append(pred)
            auc = self.metrics.get(f'{name}_auc', 0.5)
            weights.append(auc)
        
        weights = np.array(weights) / sum(weights)
        ensemble_pred = np.average(predictions, axis=0, weights=weights)
        
        # 위험 등급 계산
        risk_levels = [get_risk_level(p) for p in ensemble_pred]
        
        # 통계
        level_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        for level in risk_levels:
            level_counts[level] += 1
        
        logger.info("예측 결과 분포:")
        for level, count in level_counts.items():
            pct = count / len(risk_levels) * 100
            logger.info(f"  {level}: {count}개 ({pct:.1f}%)")
        
        if dry_run:
            logger.info("\n[DRY-RUN] DB 저장 없이 종료합니다.")
            return {
                'total': len(df),
                'distribution': level_counts,
                'predictions': list(zip(company_ids, ensemble_pred.tolist(), risk_levels))[:10]
            }
        
        # DB 저장
        prediction_date = date.today()
        model_version = self.model_data.get('config', {}).get('version', 'unknown')
        
        # 기존 예측 삭제 (동일 날짜)
        self.conn.execute(text("""
            DELETE FROM risk_predictions WHERE prediction_date = :pd
        """), {'pd': prediction_date})
        
        # 새 예측 삽입
        for i, (cid, prob, level) in enumerate(zip(company_ids, ensemble_pred, risk_levels)):
            self.conn.execute(text("""
                INSERT INTO risk_predictions (
                    company_id, prediction_date, deterioration_probability,
                    risk_level, model_version
                ) VALUES (:cid, :pd, :prob, :level, :ver)
            """), {
                'cid': cid,
                'pd': prediction_date,
                'prob': float(prob),
                'level': level,
                'ver': model_version,
            })
            
            if (i + 1) % 500 == 0:
                self.conn.commit()
                logger.info(f"  저장 진행: {i+1}/{len(company_ids)}")
        
        self.conn.commit()
        
        count = self.conn.execute(text("""
            SELECT COUNT(*) FROM risk_predictions WHERE prediction_date = :pd
        """), {'pd': prediction_date}).scalar()
        
        logger.info(f"\nrisk_predictions 테이블: {count}건 저장 완료")
        
        return {
            'total': len(df),
            'distribution': level_counts,
            'saved': count,
        }


def run_batch_prediction(model_path: str = None, dry_run: bool = False):
    """배치 추론 실행"""
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if '+asyncpg' in url:
        url = url.replace('+asyncpg', '')

    engine = create_engine(url)
    
    with engine.connect() as conn:
        predictor = BatchPredictor(conn, model_path=model_path)
        result = predictor.predict_all(dry_run=dry_run)
        
        logger.info("\n" + "=" * 60)
        logger.info("배치 추론 완료")
        logger.info("=" * 60)
        for key, value in result.items():
            if key != 'predictions':
                logger.info(f"  {key}: {value}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='배치 추론 (Phase 7)')
    parser.add_argument('--model-path', type=str, help='모델 파일 경로')
    parser.add_argument('--dry-run', action='store_true', help='DB 저장 없이 결과만 확인')
    args = parser.parse_args()

    run_batch_prediction(model_path=args.model_path, dry_run=args.dry_run)
