import { Hono } from 'hono';
import { fetchMeasurements } from '../services/measurement-service';
export const measurementRoutes = new Hono();
measurementRoutes.get('/api/measurements', async (c) => {
  return c.json(await fetchMeasurements());
});
