import { fetchFitrus } from './fitrus-client';
import { validateMeasurement } from './validation';
import { saveMeasurement } from './storage';
export async function fetchMeasurements() {
  const raw = await fetchFitrus();
  const value = validateMeasurement(raw);
  await saveMeasurement(value);
  return value;
}
