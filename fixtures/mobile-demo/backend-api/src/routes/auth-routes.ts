import { Hono } from 'hono';
import { signIn } from '../services/auth-service';
export const authRoutes = new Hono();
authRoutes.post('/api/auth/login', async (c) => {
  const body = await c.req.json();
  return c.json(await signIn(body));
});
