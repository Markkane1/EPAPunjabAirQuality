/**
 * Official Punjab Environmental Protection Council (PEPC) AQI Calculations and Color Scales in TypeScript.
 * Implements:
 * 1. T9: Statutory piecewise linear sub-index interpolation across continuous half-open intervals.
 * 2. 500 operational ceiling cap.
 * 3. Particulate-matter composite AQI: max(I_PM2.5, I_PM10).
 * 4. Official 7-category color palette and continuous 7-stop PEQS RGB gradient ramp.
 * Zero external framework dependencies.
 */

// Statutory Continuous Breakpoint Matrix (TRANSFORMATION_LOGIC_SPEC.md §2.9.2)
export const PEPC_BREAKPOINTS: Record<string, number[]> = {
  PM10: [0.0, 75.0, 150.0, 250.0, 350.0, 450.0, 550.0],
  'PM2.5': [0.0, 15.0, 35.0, 70.0, 140.0, 250.0, 350.0],
  SO2: [0.0, 60.0, 120.0, 220.0, 320.0, 800.0, 1600.0],
  NO2: [0.0, 40.0, 80.0, 130.0, 180.0, 380.0, 580.0],
  O3: [0.0, 65.0, 130.0, 195.0, 260.0, 450.0, 550.0],
  CO: [0.0, 2.5, 5.0, 7.5, 10.0, 25.0, 40.0],
};

// Sub-index tiers corresponding to category thresholds
export const AQI_TIERS: number[] = [0, 50, 100, 150, 200, 300, 400, 500];

// Official 7-Category Descriptors and Hex Palette (TRANSFORMATION_LOGIC_SPEC.md §2.9.2)
export const PEPC_CATEGORIES = [
  { index_max: 50, name: 'Good', hex: '#00B050' },
  { index_max: 100, name: 'Satisfactory', hex: '#92D050' },
  { index_max: 150, name: 'Moderate', hex: '#FFFF00' },
  { index_max: 200, name: 'Unhealthy (Sensitive)', hex: '#ED7D31' },
  { index_max: 300, name: 'Unhealthy', hex: '#FF0000' },
  { index_max: 400, name: 'Very Unhealthy', hex: '#7030A0' },
  { index_max: 500, name: 'Hazardous', hex: '#C00000' },
] as const;

// Continuous PEQS Multi-Stop Color Scale Limits & Stops (§2.9.4)
export const PEQS_MULTIPLIERS = [0.0, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0] as const;
export const PEQS_RGB_STOPS: Array<[number, number, number]> = [
  [58, 165, 93], // Clean Green
  [156, 204, 58], // Light Green
  [242, 194, 48], // Yellow (At Standard)
  [240, 122, 38], // Orange (1.5x Limit)
  [214, 52, 44], // Red (2.5x Limit)
  [142, 59, 143], // Purple (4.0x Limit)
  [90, 21, 48], // Deep Maroon (6.0x Limit)
];

export function normalizePollutantKey(pollutant: string): string {
  const clean = pollutant.trim().toUpperCase().replace(/\./g, '').replace(/_/g, '');
  if (clean === 'PM25' || clean === 'PM2') {
    return 'PM2.5';
  }
  if (clean === 'PM10' || clean === 'PM1') {
    return 'PM10';
  }
  return clean;
}

/**
 * Computes statutory Punjab Air Quality Index (AQI) sub-index for a given pollutant concentration
 * using official PEPC piecewise linear interpolation across continuous half-open intervals
 * (TRANSFORMATION_LOGIC_SPEC.md §2.9.2).
 */
export function pepcCalculateAqi(
  pollutant: string,
  concentration?: number | null
): number | null {
  if (concentration == null) {
    return null;
  }
  const c = Number(concentration);
  if (isNaN(c) || c < 0.0 || !isFinite(c)) {
    return null;
  }
  if (c === 0.0) {
    return 0;
  }

  const key = normalizePollutantKey(pollutant);
  if (!(key in PEPC_BREAKPOINTS)) {
    return null;
  }

  const bps = PEPC_BREAKPOINTS[key];
  const tiers = AQI_TIERS;

  // Operational Ceiling Cap (when PM2.5 > 350 or pollutant exceeds top breakpoint)
  if (c > bps[bps.length - 1]) {
    return 500;
  }

  // Continuous half-open intervals: (BP_low, BP_high]
  for (let i = 1; i < bps.length; i++) {
    const bpLow = bps[i - 1];
    const bpHigh = bps[i];
    if (c > bpLow && c <= bpHigh) {
      const iLow = tiers[i - 1];
      const iHigh = tiers[i];
      const val = ((iHigh - iLow) / (bpHigh - bpLow)) * (c - bpLow) + iLow;
      return Math.round(val);
    }
  }

  return 500;
}

/**
 * Computes Composite Punjab Air Quality Index (TRANSFORMATION_LOGIC_SPEC.md §2.9.3).
 * Composite AQI is strictly governed by particulate matter sub-indices: max(I_PM2.5, I_PM10).
 */
export function pepcCompositeAqi(
  pm25Aqi?: number | null,
  pm10Aqi?: number | null
): number | null {
  const valid: number[] = [];
  if (pm25Aqi != null && !isNaN(pm25Aqi)) valid.push(pm25Aqi);
  if (pm10Aqi != null && !isNaN(pm10Aqi)) valid.push(pm10Aqi);

  if (valid.length === 0) {
    return null;
  }
  return Math.max(...valid);
}

/**
 * Returns official PEPC category name descriptor for given AQI value.
 */
export function pepcGetCategory(aqi?: number | null): string {
  if (aqi == null) {
    return 'Unknown';
  }
  for (const cat of PEPC_CATEGORIES) {
    if (aqi <= cat.index_max) {
      return cat.name;
    }
  }
  return 'Hazardous';
}

/**
 * Returns official PEPC hex color string for given AQI value.
 */
export function pepcGetColor(aqi?: number | null): string {
  if (aqi == null) {
    return '#808080'; // Neutral gray
  }
  for (const cat of PEPC_CATEGORIES) {
    if (aqi <= cat.index_max) {
      return cat.hex;
    }
  }
  return '#C00000';
}

/**
 * Computes continuous 7-stop PEQS RGB color vector relative to statutory standard limit
 * (TRANSFORMATION_LOGIC_SPEC.md §2.9.4).
 */
export function pepcInterpolateColor(
  value: number,
  refLimit: number
): [r: number, g: number, b: number] {
  if (refLimit <= 0.0 || value <= 0.0 || isNaN(value)) {
    return PEQS_RGB_STOPS[0];
  }

  const multVal = value / refLimit;
  const numStops = PEQS_MULTIPLIERS.length;

  if (multVal <= PEQS_MULTIPLIERS[0]) {
    return PEQS_RGB_STOPS[0];
  }
  if (multVal >= PEQS_MULTIPLIERS[numStops - 1]) {
    return PEQS_RGB_STOPS[numStops - 1];
  }

  for (let k = 1; k < numStops; k++) {
    const m0 = PEQS_MULTIPLIERS[k - 1];
    const m1 = PEQS_MULTIPLIERS[k];
    if (multVal >= m0 && multVal <= m1) {
      const t = (multVal - m0) / (m1 - m0);
      const c0 = PEQS_RGB_STOPS[k - 1];
      const c1 = PEQS_RGB_STOPS[k];
      const r = Math.round((1.0 - t) * c0[0] + t * c1[0]);
      const g = Math.round((1.0 - t) * c0[1] + t * c1[1]);
      const b = Math.round((1.0 - t) * c0[2] + t * c1[2]);
      return [r, g, b];
    }
  }

  return PEQS_RGB_STOPS[numStops - 1];
}

/**
 * Returns continuous 7-stop PEQS interpolated color formatted as a Hex string '#RRGGBB'.
 */
export function pepcInterpolateColorHex(value: number, refLimit: number): string {
  const [r, g, b] = pepcInterpolateColor(value, refLimit);
  const toHex = (n: number) => n.toString(16).padStart(2, '0').toUpperCase();
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
