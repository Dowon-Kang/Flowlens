export function validateMeasurement(value: unknown) {
  if (!value) throw new Error('Missing measurement');
  return value;
}
