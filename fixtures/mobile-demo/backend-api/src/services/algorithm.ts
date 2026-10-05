import { validateMeasurement } from './validation';
import { getRule } from './rule-store';
export function recommend(value: unknown) {
  const validated = validateMeasurement(value);
  return { mode: 'MOCK_ONLY', rule: getRule(), data: validated };
}
