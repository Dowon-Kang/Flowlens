export async function fetchFitrus() {
  // Synthetic URL: not a real FITRUS endpoint.
  const response = await fetch('https://fitrus.example.invalid/measurements');
  return response.json();
}
