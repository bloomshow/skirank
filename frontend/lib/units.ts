export type UnitSystem = "metric" | "imperial";

export function detectUnitSystem(): UnitSystem {
  if (typeof navigator === "undefined") return "metric";
  const locale = navigator.language || "en-US";
  if (
    locale.startsWith("en-US") ||
    locale === "en-LR" ||
    locale.startsWith("my")
  ) {
    return "imperial";
  }
  return "metric";
}

export const convert = {
  cmToIn: (cm: number) => Math.round(cm * 0.394),
  cToF: (c: number) => Math.round((c * 9) / 5 + 32),
  kmhToMph: (kmh: number) => Math.round(kmh * 0.621),
};

interface FormattedValue {
  primary: string;
  secondary: string;
}

export function fmtDepth(
  cm: number | null | undefined,
  units: UnitSystem
): FormattedValue {
  if (cm === null || cm === undefined) return { primary: "—", secondary: "" };
  const inches = convert.cmToIn(cm);
  if (units === "imperial") return { primary: `${inches}"`, secondary: `${cm}cm` };
  return { primary: `${cm}cm`, secondary: `${inches}"` };
}

export function fmtSnow(
  cm: number | null | undefined,
  units: UnitSystem
): FormattedValue {
  if (cm === null || cm === undefined || cm === 0)
    return { primary: "—", secondary: "" };
  const inches = convert.cmToIn(cm);
  if (units === "imperial") return { primary: `${inches}"`, secondary: `${cm}cm` };
  return { primary: `${cm}cm`, secondary: `${inches}"` };
}

export function fmtTemp(
  c: number | null | undefined,
  units: UnitSystem
): FormattedValue {
  if (c === null || c === undefined) return { primary: "—", secondary: "" };
  const f = convert.cToF(c);
  if (units === "imperial") return { primary: `${f}°F`, secondary: `${c}°C` };
  return { primary: `${c}°C`, secondary: `${f}°F` };
}

export function fmtWind(
  kmh: number | null | undefined,
  units: UnitSystem
): FormattedValue {
  if (kmh === null || kmh === undefined) return { primary: "—", secondary: "" };
  const mph = convert.kmhToMph(kmh);
  if (units === "imperial")
    return { primary: `${mph} mph`, secondary: `${kmh} km/h` };
  return { primary: `${kmh} km/h`, secondary: `${mph} mph` };
}
