// deltaScale v1.1 — robust, dependency-free.
// Usage: import { deltaScale, thresholdFor } from "./receipts-kit/deltaScale.js";

export const SCALE = ["min","hour","day","week","month","quarter","year"];

export const THRESHOLDS = {
  equity:   { min_hour: 0.02,  hour_day: 0.035, day_week: 0.05 },
  fx:       { min_hour: 0.008, hour_day: 0.015, day_week: 0.025 },
  crypto:   { min_hour: 0.08,  hour_day: 0.12,  day_week: 0.18 },
  commodity:{ min_hour: 0.025, hour_day: 0.04,  day_week: 0.06 },
  bond:     { min_hour: 0.005, hour_day: 0.01,  day_week: 0.015 },
  default:  { min_hour: 0.03,  hour_day: 0.05,  day_week: 0.08 }
};

// opts: { ref: "A"|"B"|"mean", winsor: 0..0.2 }
export function deltaScale(pathAgg = [], pathDirect = [], opts = {}) {
  const { ref = "B", winsor = 0.0 } = opts;
  if (!Array.isArray(pathAgg) || !Array.isArray(pathDirect) || pathAgg.length !== pathDirect.length || pathAgg.length === 0) {
    return { delta_scale: 0, max_deviation: 0, mean_ratio: 1, n: 0 };
  }
  const clean = (x) => Number.isFinite(x) ? x : 0;
  const A = pathAgg.map(v => clean(Number(v)));
  const B = pathDirect.map(v => clean(Number(v)));
  const n = A.length;

  const winsorize = (arr, w) => {
    if (!w) return arr;
    const t = [...arr].sort((x,y)=>x-y);
    const lo = t[Math.floor(w * (n-1))];
    const hi = t[Math.ceil((1-w) * (n-1))];
    return arr.map(v => Math.min(hi, Math.max(lo, v)));
  };
  const Aw = winsorize(A, winsor);
  const Bw = winsorize(B, winsor);

  let sumAbsRef = 0, sumAbsDiff = 0, maxAbsDiff = 0, sumA = 0, sumB = 0;
  for (let i = 0; i < n; i++) {
    const a = Aw[i], b = Bw[i];
    const diff = Math.abs(a - b);
    sumAbsDiff += diff;
    if (diff > maxAbsDiff) maxAbsDiff = diff;

    const refVal = ref === "A" ? Math.abs(a) : ref === "mean" ? (Math.abs(a)+Math.abs(b))/2 : Math.abs(b);
    sumAbsRef += refVal;

    sumA += a; sumB += b;
  }
  const denom = (sumAbsRef / n) || 1e-8;
  return {
    delta_scale: (sumAbsDiff / n) / denom,
    max_deviation: maxAbsDiff / denom,
    mean_ratio: (sumA / n) / ((sumB / n) || 1e-8),
    n
  };
}

export function thresholdFor(assetClass = "default", from = "min", to = "hour") {
  const table = THRESHOLDS[assetClass] || THRESHOLDS.default;
  const key = `${from}_${to}`;
  if (table[key] != null) return table[key];

  const i = SCALE.indexOf(from), j = SCALE.indexOf(to);
  const dist = (i === -1 || j === -1) ? 1 : Math.abs(j - i);
  if (dist === 1) return table.min_hour;
  if (dist === 2) return table.hour_day;
  return table.day_week;
}
