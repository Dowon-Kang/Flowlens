import { Hono } from 'hono';
import { recommend } from '../services/algorithm';
export const recommendationRoutes = new Hono();
recommendationRoutes.post('/api/recommendations', async (c) => {
  const input = await c.req.json();
  return c.json(recommend(input));
});
