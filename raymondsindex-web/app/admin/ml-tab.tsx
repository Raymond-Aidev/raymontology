'use client';

import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';

// =============================================================================
// Types
// =============================================================================

interface ModelInfo {
  version: string;
  type: string;
  is_active: boolean;
  auc_roc: number;
  precision_at_10: number;
  recall: number;
  brier_score: number;
  training_date: string;
  training_samples: number;
  feature_count: number;
}

interface FeatureStat {
  name: string;
  category: string;
  null_count: number;
  null_rate: number;
  mean: number | null;
  std: number | null;
  min_val: number | null;
  max_val: number | null;
  health: 'healthy' | 'warning' | 'critical';
}

interface RiskLevelStat {
  count: number;
  pct: number;
  avg_prob: number;
}

interface DistributionBucket {
  range: string;
  count: number;
  pct: number;
}

interface MLOverview {
  active_model: ModelInfo | null;
  prediction_summary: {
    total_companies: number;
    distribution: Record<string, number>;
    last_prediction_date: string | null;
  };
  feature_health: {
    total_features: number;
    healthy: number;
    warning: number;
    critical: number;
    avg_null_rate: number;
  };
  detection_rates: Record<string, number>;
}

interface DetectionStat {
  total: number;
  by_risk_level: Record<string, { count: number; pct: number }>;
}

interface TrainStatus {
  task_id: string | null;
  status: string;
  phase: string | null;
  progress: number;
  phases: Array<{ name: string; status: string }>;
  started_at: string | null;
  elapsed_sec: number | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

type SubTab = 'models' | 'distribution' | 'features' | 'training';

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#7C2D12',
  HIGH: '#EF4444',
  MEDIUM: '#F59E0B',
  LOW: '#22C55E',
};

const HEALTH_ICONS: Record<string, string> = {
  healthy: '✅',
  warning: '⚠️',
  critical: '❌',
};

const CATEGORY_LABELS: Record<string, string> = {
  officer: '임원',
  cb: 'CB',
  shareholder: '대주주',
  index: '인덱스',
};

// =============================================================================
// Component
// =============================================================================

export default function MLTab({ token }: { token: string }) {
  const [subTab, setSubTab] = useState<SubTab>('models');
  const [overview, setOverview] = useState<MLOverview | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [features, setFeatures] = useState<FeatureStat[]>([]);
  const [distribution, setDistribution] = useState<{
    histogram: DistributionBucket[];
    by_risk_level: Record<string, RiskLevelStat>;
    by_market: Record<string, Record<string, number>>;
  } | null>(null);
  const [validation, setValidation] = useState<{
    suspended_detection: DetectionStat;
    managed_detection: DetectionStat;
  } | null>(null);
  const [trainStatus, setTrainStatus] = useState<TrainStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovRes, modRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/ml/overview`, { headers }),
        fetch(`${API_BASE_URL}/admin/ml/models`, { headers }),
      ]);

      if (ovRes.ok) setOverview(await ovRes.json());
      if (modRes.ok) setModels(await modRes.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  const fetchSubTabData = useCallback(async () => {
    try {
      if (subTab === 'features') {
        const res = await fetch(`${API_BASE_URL}/admin/ml/features/stats`, { headers });
        if (res.ok) {
          const data = await res.json();
          setFeatures(data.features);
        }
      } else if (subTab === 'distribution') {
        const [distRes, valRes] = await Promise.all([
          fetch(`${API_BASE_URL}/admin/ml/predictions/distribution`, { headers }),
          fetch(`${API_BASE_URL}/admin/ml/predictions/validation`, { headers }),
        ]);
        if (distRes.ok) setDistribution(await distRes.json());
        if (valRes.ok) setValidation(await valRes.json());
      } else if (subTab === 'training') {
        const res = await fetch(`${API_BASE_URL}/admin/ml/train/status`, { headers });
        if (res.ok) setTrainStatus(await res.json());
      }
    } catch (e) {
      console.error('SubTab data fetch error:', e);
    }
  }, [subTab, token]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchSubTabData(); }, [fetchSubTabData]);

  // Training status polling
  useEffect(() => {
    if (trainStatus?.status !== 'running') return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/admin/ml/train/status`, { headers });
        if (res.ok) setTrainStatus(await res.json());
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [trainStatus?.status]);

  const handleActivateModel = async (version: string) => {
    if (!confirm(`모델 ${version}을 활성화하시겠습니까?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/admin/ml/models/${version}/activate`, {
        method: 'POST', headers,
      });
      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      setError(String(e));
    }
  };

  const handleStartTraining = async () => {
    const version = prompt('새 모델 버전을 입력하세요 (e.g. v3.0.0):');
    if (!version) return;

    try {
      const res = await fetch(`${API_BASE_URL}/admin/ml/train`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ version, run_batch_prediction: true }),
      });
      if (res.ok) {
        const data = await res.json();
        setTrainStatus({
          task_id: data.task_id,
          status: 'running',
          phase: 'initializing',
          progress: 0,
          phases: [],
          started_at: new Date().toISOString(),
          elapsed_sec: 0,
          result: null,
          error: null,
        });
        setSubTab('training');
      } else {
        const err = await res.json();
        alert(err.detail || '학습 시작 실패');
      }
    } catch (e) {
      alert(String(e));
    }
  };

  if (loading) return <div className="text-center py-12 text-gray-500">로딩 중...</div>;

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
      )}

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Model Card */}
          <div className="bg-white border rounded-lg p-4">
            <div className="text-xs text-gray-500 mb-1">활성 모델</div>
            <div className="text-2xl font-bold text-blue-600">
              {overview.active_model?.version || 'N/A'}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              AUC {overview.active_model?.auc_roc.toFixed(4)}
            </div>
          </div>

          {/* Prediction Card */}
          <div className="bg-white border rounded-lg p-4">
            <div className="text-xs text-gray-500 mb-1">예측 기업</div>
            <div className="text-2xl font-bold">
              {overview.prediction_summary.total_companies.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              CRITICAL {overview.prediction_summary.distribution.CRITICAL || 0}
              <span className="text-gray-400 ml-1">
                ({((overview.prediction_summary.distribution.CRITICAL || 0) / overview.prediction_summary.total_companies * 100).toFixed(1)}%)
              </span>
            </div>
          </div>

          {/* Feature Health Card */}
          <div className="bg-white border rounded-lg p-4">
            <div className="text-xs text-gray-500 mb-1">피처 건강</div>
            <div className="text-2xl font-bold text-green-600">
              {overview.feature_health.healthy}/{overview.feature_health.total_features}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              {overview.feature_health.warning > 0 && (
                <span className="text-yellow-600 mr-2">⚠ {overview.feature_health.warning}</span>
              )}
              {overview.feature_health.critical > 0 && (
                <span className="text-red-600">{"❌"} {overview.feature_health.critical}</span>
              )}
            </div>
          </div>

          {/* Detection Rate Card */}
          <div className="bg-white border rounded-lg p-4">
            <div className="text-xs text-gray-500 mb-1">탐지율</div>
            <div className="text-2xl font-bold text-purple-600">
              {overview.detection_rates.suspended_critical}%
            </div>
            <div className="text-sm text-gray-600 mt-1">
              SUSPENDED → CRITICAL
            </div>
          </div>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {([
          ['models', '모델 비교'],
          ['distribution', '예측 분포'],
          ['features', '피처 모니터링'],
          ['training', '학습 제어'],
        ] as [SubTab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setSubTab(key)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              subTab === key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Sub-tab Content */}
      {subTab === 'models' && <ModelsPanel models={models} onActivate={handleActivateModel} validation={validation} />}
      {subTab === 'distribution' && distribution && <DistributionPanel data={distribution} />}
      {subTab === 'features' && <FeaturesPanel features={features} categoryFilter={categoryFilter} setCategoryFilter={setCategoryFilter} />}
      {subTab === 'training' && <TrainingPanel trainStatus={trainStatus} onStartTraining={handleStartTraining} />}
    </div>
  );
}

// =============================================================================
// Sub-panels
// =============================================================================

function ModelsPanel({
  models, onActivate, validation,
}: {
  models: ModelInfo[];
  onActivate: (v: string) => void;
  validation: { suspended_detection: DetectionStat; managed_detection: DetectionStat } | null;
}) {
  return (
    <div className="space-y-4">
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">버전</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">AUC-ROC</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">P@10%</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Recall</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Brier</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">학습일</th>
              <th className="px-4 py-3 text-center font-medium text-gray-700">상태</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {models.map((m) => (
              <tr key={m.version} className={m.is_active ? 'bg-blue-50/50' : ''}>
                <td className="px-4 py-3 font-mono font-medium">{m.version}</td>
                <td className="px-4 py-3 text-right font-mono">{m.auc_roc.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono">{m.precision_at_10.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono">{m.recall.toFixed(4)}</td>
                <td className="px-4 py-3 text-right font-mono">{m.brier_score.toFixed(4)}</td>
                <td className="px-4 py-3 text-right text-gray-600">{m.training_date}</td>
                <td className="px-4 py-3 text-center">
                  {m.is_active ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                      ● 활성
                    </span>
                  ) : (
                    <button
                      onClick={() => onActivate(m.version)}
                      className="text-xs text-gray-500 hover:text-blue-600 underline"
                    >
                      활성화
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {validation && (
        <div className="grid grid-cols-2 gap-4">
          <DetectionCard title="거래정지 탐지" data={validation.suspended_detection} />
          <DetectionCard title="관리종목 탐지" data={validation.managed_detection} />
        </div>
      )}
    </div>
  );
}

function DetectionCard({ title, data }: { title: string; data: DetectionStat }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <h4 className="text-sm font-medium text-gray-700 mb-3">{title} ({data.total}개)</h4>
      <div className="space-y-2">
        {Object.entries(data.by_risk_level)
          .sort(([a], [b]) => {
            const order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
            return order.indexOf(a) - order.indexOf(b);
          })
          .map(([level, stat]) => (
          <div key={level} className="flex items-center gap-2">
            <div className="w-20 text-xs font-medium" style={{ color: RISK_COLORS[level] }}>{level}</div>
            <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${stat.pct}%`, backgroundColor: RISK_COLORS[level] }}
              />
            </div>
            <div className="w-20 text-right text-xs text-gray-600">
              {stat.count} ({stat.pct}%)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DistributionPanel({
  data,
}: {
  data: {
    histogram: DistributionBucket[];
    by_risk_level: Record<string, RiskLevelStat>;
    by_market: Record<string, Record<string, number>>;
  };
}) {
  const maxCount = Math.max(...data.histogram.map(h => h.count));

  return (
    <div className="space-y-4">
      {/* Histogram */}
      <div className="bg-white border rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">확률 분포 히스토그램</h4>
        <div className="space-y-1">
          {data.histogram.map((bucket) => {
            const prob = parseFloat(bucket.range.split('-')[0]);
            let color = '#22C55E';
            if (prob >= 0.7) color = '#7C2D12';
            else if (prob >= 0.5) color = '#EF4444';
            else if (prob >= 0.3) color = '#F59E0B';

            return (
              <div key={bucket.range} className="flex items-center gap-2">
                <div className="w-16 text-xs text-gray-500 text-right font-mono">{bucket.range}</div>
                <div className="flex-1 bg-gray-100 rounded h-5 overflow-hidden">
                  <div
                    className="h-full rounded transition-all"
                    style={{
                      width: `${(bucket.count / maxCount) * 100}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <div className="w-20 text-right text-xs text-gray-600">
                  {bucket.count} ({bucket.pct}%)
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Risk Level Summary */}
      <div className="grid grid-cols-4 gap-3">
        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => {
          const stat = data.by_risk_level[level];
          if (!stat) return null;
          return (
            <div
              key={level}
              className="border rounded-lg p-3 text-center"
              style={{ borderColor: RISK_COLORS[level] }}
            >
              <div className="text-xs font-medium" style={{ color: RISK_COLORS[level] }}>{level}</div>
              <div className="text-xl font-bold mt-1">{stat.count.toLocaleString()}</div>
              <div className="text-xs text-gray-500">{stat.pct}% | avg {stat.avg_prob.toFixed(2)}</div>
            </div>
          );
        })}
      </div>

      {/* Market Distribution */}
      {Object.keys(data.by_market).length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">시장별 분포</h4>
          <div className="space-y-2">
            {Object.entries(data.by_market).map(([market, levels]) => {
              const total = Object.values(levels).reduce((a, b) => a + b, 0);
              return (
                <div key={market} className="flex items-center gap-2">
                  <div className="w-16 text-xs font-medium text-gray-700">{market}</div>
                  <div className="flex-1 flex h-6 rounded overflow-hidden">
                    {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => {
                      const cnt = levels[level] || 0;
                      if (cnt === 0) return null;
                      return (
                        <div
                          key={level}
                          className="h-full"
                          style={{
                            width: `${(cnt / total) * 100}%`,
                            backgroundColor: RISK_COLORS[level],
                          }}
                          title={`${level}: ${cnt} (${(cnt/total*100).toFixed(1)}%)`}
                        />
                      );
                    })}
                  </div>
                  <div className="w-12 text-xs text-gray-500 text-right">{total}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function FeaturesPanel({
  features, categoryFilter, setCategoryFilter,
}: {
  features: FeatureStat[];
  categoryFilter: string;
  setCategoryFilter: (v: string) => void;
}) {
  const filtered = categoryFilter === 'all'
    ? features
    : features.filter(f => f.category === categoryFilter);

  return (
    <div className="space-y-4">
      {/* Category Filter */}
      <div className="flex gap-2">
        {['all', 'officer', 'cb', 'shareholder', 'index'].map(cat => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              categoryFilter === cat
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat === 'all' ? '전체' : CATEGORY_LABELS[cat] || cat}
          </button>
        ))}
      </div>

      {/* Feature Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">피처</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">카테고리</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">NULL%</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">평균</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">표준편차</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Min</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Max</th>
              <th className="px-4 py-3 text-center font-medium text-gray-700">상태</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map(f => (
              <tr key={f.name} className={f.health === 'critical' ? 'bg-red-50/50' : f.health === 'warning' ? 'bg-yellow-50/30' : ''}>
                <td className="px-4 py-2 font-mono text-xs">{f.name}</td>
                <td className="px-4 py-2 text-xs text-gray-500">{CATEGORY_LABELS[f.category]}</td>
                <td className="px-4 py-2 text-right font-mono text-xs">
                  <span className={f.null_rate > 50 ? 'text-red-600 font-bold' : f.null_rate > 10 ? 'text-yellow-600' : 'text-green-600'}>
                    {f.null_rate.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-2 text-right font-mono text-xs text-gray-600">{f.mean?.toFixed(2) ?? '-'}</td>
                <td className="px-4 py-2 text-right font-mono text-xs text-gray-600">{f.std?.toFixed(2) ?? '-'}</td>
                <td className="px-4 py-2 text-right font-mono text-xs text-gray-400">{f.min_val?.toFixed(2) ?? '-'}</td>
                <td className="px-4 py-2 text-right font-mono text-xs text-gray-400">{f.max_val?.toFixed(2) ?? '-'}</td>
                <td className="px-4 py-2 text-center">{HEALTH_ICONS[f.health]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TrainingPanel({
  trainStatus, onStartTraining,
}: {
  trainStatus: TrainStatus | null;
  onStartTraining: () => void;
}) {
  const isRunning = trainStatus?.status === 'running';

  return (
    <div className="space-y-4">
      {/* Start Training Button */}
      <div className="bg-white border rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-gray-700">모델 재학습</h4>
            <p className="text-xs text-gray-500 mt-1">
              현재 피처 데이터로 새 모델을 학습합니다
            </p>
          </div>
          <button
            onClick={onStartTraining}
            disabled={isRunning}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              isRunning
                ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isRunning ? '학습 중...' : '학습 시작'}
          </button>
        </div>
      </div>

      {/* Training Progress */}
      {trainStatus && trainStatus.task_id && (
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-700">
              학습 진행 상황
              <span className="ml-2 text-xs text-gray-400">{trainStatus.task_id}</span>
            </h4>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              trainStatus.status === 'completed' ? 'bg-green-100 text-green-700' :
              trainStatus.status === 'running' ? 'bg-blue-100 text-blue-700' :
              trainStatus.status === 'failed' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {trainStatus.status}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${
                trainStatus.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{ width: `${trainStatus.progress}%` }}
            />
          </div>

          {/* Phases */}
          <div className="space-y-2">
            {trainStatus.phases.map((phase, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="w-4 text-center">
                  {phase.status === 'completed' ? '✅' :
                   phase.status === 'in_progress' ? '⟳' :
                   phase.status === 'failed' ? '❌' :
                   phase.status === 'skipped' ? '⏭' : '⏳'}
                </span>
                <span className={`${phase.status === 'in_progress' ? 'text-blue-700 font-medium' : 'text-gray-600'}`}>
                  {phase.name}
                </span>
              </div>
            ))}
          </div>

          {/* Elapsed time */}
          {trainStatus.elapsed_sec != null && (
            <div className="mt-3 text-xs text-gray-500">
              경과: {Math.floor(trainStatus.elapsed_sec / 60)}분 {trainStatus.elapsed_sec % 60}초
            </div>
          )}

          {/* Error */}
          {trainStatus.error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
              {trainStatus.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
