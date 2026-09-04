const SITE_KEYWORDS =
  /\b(completed|complete|progress|foundation|pour|erection|piping|wbs|activity|sector|rack|spool|hydro|concrete|rebar|inspection|curing|steel|supervisor|dpr|field\s+report|percent|%)\b/i;

const WBS_PATTERN = /\b[A-Z]{2,4}[-_]?\d{2,4}[-_]?\d{2,4}\b/;

const CODE_OR_NON_SITE_PATTERNS =
  /\b(function|import\s+|export\s+|class\s+\w|def\s+\w|const\s+\w|let\s+\w|SELECT\s+|INSERT\s+|<!DOCTYPE|<html|<script|npm\s+install|package\.json|\{\s*"name"\s*:)\b/i;

export type ContentValidationResult = {
  isValid: boolean;
  reason?: string;
};

export async function readFileAsText(file: File): Promise<string> {
  if (file.name.toLowerCase().endsWith('.xlsx')) {
    return '';
  }
  try {
    return await file.text();
  } catch {
    return '';
  }
}

export function looksLikeSiteReport(text: string, filename?: string): ContentValidationResult {
  const trimmed = text.trim();
  const fname = (filename ?? '').toLowerCase();

  if (fname.endsWith('.xlsx') || fname.endsWith('.csv')) {
    if (fname.includes('dpr') || fname.includes('progress') || fname.includes('report') || fname.includes('wbs')) {
      return { isValid: true };
    }
    if (trimmed && (SITE_KEYWORDS.test(trimmed) || WBS_PATTERN.test(trimmed))) {
      return { isValid: true };
    }
    return {
      isValid: false,
      reason: 'Spreadsheet does not match expected DPR or discipline report naming conventions.',
    };
  }

  if (!trimmed) {
    return { isValid: false, reason: 'File is empty or could not be read as text.' };
  }

  const sample = trimmed.slice(0, 2000);
  if (CODE_OR_NON_SITE_PATTERNS.test(sample)) {
    return {
      isValid: false,
      reason: 'Content appears to be source code or non-operational text, not a field site report.',
    };
  }

  if (SITE_KEYWORDS.test(sample) || WBS_PATTERN.test(sample)) {
    return { isValid: true };
  }

  return {
    isValid: false,
    reason: 'No construction activity keywords or WBS identifiers detected in file content.',
  };
}
