import { Hono } from 'hono';
import { authRoutes } from './routes/auth-routes';
import { measurementRoutes } from './routes/measurement-routes';
import { recommendationRoutes } from './routes/recommendation-routes';
const app = new Hono();
app.route('/', authRoutes);
app.route('/', measurementRoutes);
app.route('/', recommendationRoutes);
export default app;
