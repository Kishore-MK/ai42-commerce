import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { serve } from '@hono/node-server';
import { config } from 'dotenv'; 
import agents from './routes/agent.js';
import keys from './routes/keys.js';

// Load environment variables
config();

const app = new Hono();

// CORS middleware
app.use('/*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
}));

// Health check endpoint
app.get('/', (c) => {
  return c.json({ message: 'Agent Registry Service is running' });
});

// Mount routes
app.route('/agents', agents);
app.route('/', keys);
 

const port = parseInt(process.env.PORT || '9002');

console.log('🏁 Agent Registry Service started successfully');
console.log(`🚀 Server running on http://localhost:${port}`);

serve({
  fetch: app.fetch,
  port,
});