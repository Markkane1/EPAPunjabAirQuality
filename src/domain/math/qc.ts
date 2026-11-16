/**
 * Temporal Quality Control (QC), Outlier Scrubbing, Completeness Rules, and Animation Lerp in TypeScript.
 * Implements:
 * 1. T10: Step 0 zero/negative purge.
 * 2. 7-hour rolling median spike filter (>4M and >3ref).
 * 3. 3-hour logger hold (sensor freeze) filter with i >= 2 index guard (AQI exempt).
 * 4. 75% temporal completeness aggregation rule.
 * 5. Continuous sub-hourly linear interpolation (lerp) for 60 FPS animation scrubbing.
 * Zero external framework dependencies.
 */

export const DEFAULT_COMPLETENESS_RATIO = 0.75;
export const MEDIAN_WINDOW_HALF_WIDTH = 3; // 7-hour rolling window: [i - 3, i + 3]
export const MIN_MEDIAN_WINDOW_SAMPLES = 3;
export const SPIKE_MEDIAN_MULTIPLIER = 4.0;
export const SPIKE_REF_MULTIPLIER = 3.0;

/**
 * Sanitizes zero/negatives, cleans 7-hour rolling median spikes, and purges 3-hour logger holds
 * (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
 */
export function temporalQcClean(
  series: Array<number | null | undefined>,
  refLimit: number,
  pollutant: string
): [cleanedSeries: Array<number | null>, spikeCount: number] {
  if (!series || series.length === 0) {
    return [[], 0];
  }

  // Step 0: Zero and negative purge
  const cleaned: Array<number | null> = [];
  for (const v of series) {
    if (v == null) {
      cleaned.push(null);
      continue;
    }
    const fv = Number(v);
    if (isNaN(fv) || fv <= 0.0 || !isFinite(fv)) {
      cleaned.push(null);
    } else {
      cleaned.push(fv);
    }
  }

  const n = cleaned.length;
  let spikeCount = 0;

  // Step 1: 7-Hour Rolling Window Median Spike Filter
  for (let i = 0; i < n; i++) {
    const curr = cleaned[i];
    if (curr == null) continue;

    const wStart = Math.max(0, i - MEDIAN_WINDOW_HALF_WIDTH);
    const wEnd = Math.min(n, i + MEDIAN_WINDOW_HALF_WIDTH + 1);
    const window: number[] = [];

    for (let j = wStart; j < wEnd; j++) {
      if (cleaned[j] != null) {
        window.push(cleaned[j]!);
      }
    }

    if (window.length >= MIN_MEDIAN_WINDOW_SAMPLES) {
      window.sort((a, b) => a - b);
      const mid = Math.floor(window.length / 2);
      let medianVal: number;
      if (window.length % 2 !== 0) {
        medianVal = window[mid];
      } else {
        medianVal = (window[mid - 1] + window[mid]) / 2.0;
      }

      if (
        curr > SPIKE_MEDIAN_MULTIPLIER * medianVal &&
        curr > SPIKE_REF_MULTIPLIER * refLimit
      ) {
        cleaned[i] = null;
        spikeCount++;
      }
    }
  }

  // Step 2: 3-Hour Logger Hold (Sensor Freeze) Filter with Index Guard (i >= 2)
  // Physical pollutants only; dimensionless integer 'AQI' is exempt
  if (pollutant.trim().toUpperCase() !== 'AQI') {
    const preHold = [...cleaned];
    for (let i = 2; i < n; i++) {
      const v0 = preHold[i];
      const v1 = preHold[i - 1];
      const v2 = preHold[i - 2];
      if (v0 != null && v1 != null && v2 != null) {
        if (v0 === v1 && v1 === v2) {
          cleaned[i] = null;
        }
      }
    }
  }

  return [cleaned, spikeCount];
}

/**
 * Evaluates regulatory 75% temporal completeness rule for time aggregation
 * (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
 */
export function checkCompleteness(
  series: Array<number | null | undefined>,
  requiredRatio: number = DEFAULT_COMPLETENESS_RATIO
): number | null {
  const totalHours = series.length;
  if (totalHours === 0) {
    return null;
  }

  const validValues: number[] = [];
  for (const v of series) {
    if (v != null && !isNaN(v)) {
      validValues.push(Number(v));
    }
  }

  const nValid = validValues.length;
  const minRequired = Math.max(1, Math.round(requiredRatio * totalHours));
  if (nValid < minRequired) {
    return null;
  }

  const sum = validValues.reduce((acc, val) => acc + val, 0);
  return sum / nValid;
}

/**
 * Continuous sub-hourly linear interpolation for smooth 60 FPS animation scrubbing
 * (TRANSFORMATION_LOGIC_SPEC.md §2.10.1).
 */
export function subhourlyLerp(
  series: Array<number | null | undefined>,
  fp: number
): number | null {
  const n = series.length;
  if (n === 0) return null;
  if (n === 1) return series[0] ?? null;

  // Clamp fp to valid index bounds [0.0, n - 1.0]
  const clampedFp = Math.max(0.0, Math.min(Number(n - 1), fp));
  const i = Math.floor(clampedFp);
  const j = Math.min(n - 1, i + 1);
  const f = clampedFp - i;

  const a = series[i] ?? null;
  const b = series[j] ?? null;

  if (a == null && b == null) return null;
  if (a == null) return b;
  if (b == null) return a;

  return a + (b - a) * f;
}
