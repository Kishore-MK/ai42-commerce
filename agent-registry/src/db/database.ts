// © 2025 Visa.
// Licensed under MIT License

import Database from 'better-sqlite3';
import {
  CREATE_AGENTS_TABLE,
  CREATE_AGENT_KEYS_TABLE,
  CREATE_AGENTS_INDEX,
  CREATE_AGENT_KEYS_INDEX,
  CREATE_AGENT_KEYS_KEY_ID_INDEX,
} from './schema.js';
import type { Agent, AgentKey, AgentWithKeys } from '../types/index.js';

const DB_PATH = process.env.DATABASE_PATH || './agent_registry.db';

export const db = new Database(DB_PATH);

// Enable foreign keys
db.pragma('foreign_keys = ON');

/**
 * Initialize database tables
 */
export function initDb() {
  db.exec(CREATE_AGENTS_TABLE);
  db.exec(CREATE_AGENT_KEYS_TABLE);
  db.exec(CREATE_AGENTS_INDEX);
  db.exec(CREATE_AGENT_KEYS_INDEX);
  db.exec(CREATE_AGENT_KEYS_KEY_ID_INDEX);
  console.log('📊 Database initialized successfully');
}

// Initialize database immediately
initDb();

// Agent queries
export const agentQueries = {
  getAll: db.prepare<[]>('SELECT * FROM agents WHERE is_active = ?'),
  getById: db.prepare<[number]>('SELECT * FROM agents WHERE id = ?'),
  getByDomain: db.prepare<[string]>('SELECT * FROM agents WHERE domain = ?'),
  
  create: db.prepare<[string, string, string | null, string | null, string]>(
    'INSERT INTO agents (name, domain, description, contact_email, is_active) VALUES (?, ?, ?, ?, ?)'
  ),
  
  update: db.prepare(
    'UPDATE agents SET name = ?, description = ?, contact_email = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ),
  
  deactivate: db.prepare<[number]>(
    "UPDATE agents SET is_active = 'false', updated_at = CURRENT_TIMESTAMP WHERE id = ?"
  ),
};

// Agent key queries
export const keyQueries = {
  getByAgentId: db.prepare<[number]>('SELECT * FROM agent_keys WHERE agent_id = ?'),
  
  getByKeyId: db.prepare<[string]>('SELECT * FROM agent_keys WHERE key_id = ?'),
  
  getByAgentAndKeyId: db.prepare<[number, string]>(
    'SELECT * FROM agent_keys WHERE agent_id = ? AND key_id = ?'
  ),
  
  create: db.prepare<[number, string, string, string, string | null, string]>(
    'INSERT INTO agent_keys (agent_id, key_id, public_key, algorithm, description, is_active) VALUES (?, ?, ?, ?, ?, ?)'
  ),
  
  update: db.prepare(
    'UPDATE agent_keys SET key_id = ?, public_key = ?, algorithm = ?, description = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
  ),
  
  delete: db.prepare<[number]>('DELETE FROM agent_keys WHERE id = ?'),
};

/**
 * Get agent with all keys
 */
export function getAgentWithKeys(agentId: number): AgentWithKeys | null {
  const agent = agentQueries.getById.get(agentId) as Agent | undefined;
  if (!agent) return null;
  
  const keys = keyQueries.getByAgentId.all(agentId) as AgentKey[];
  
  return {
    ...agent,
    keys,
  };
}

/**
 * Get all agents with keys
 */
export function getAllAgentsWithKeys(activeOnly: boolean = true): AgentWithKeys[] {
  const agents = agentQueries.getAll.all() as Agent[];
  
  return agents.map(agent => ({
    ...agent,
    keys: keyQueries.getByAgentId.all(agent.id) as AgentKey[],
  }));
}


 