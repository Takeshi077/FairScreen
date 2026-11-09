export function fmt(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(digits);
}

export function signed(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

export function percent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function points(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return `${(value * 100).toFixed(digits)} points`;
}

export function yesNo(value: boolean | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not applicable";
  }
  return value ? "Yes" : "No";
}

export function shortRunId(id: string): string {
  return id.slice(0, 8);
}
