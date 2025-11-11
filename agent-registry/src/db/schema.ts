export const CREATE_AGENTS_TABLE = `
  CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT NOT NULL UNIQUE,
    description TEXT,
    contact_email TEXT,
    is_active TEXT NOT NULL DEFAULT 'true',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  )
`;

export const CREATE_AGENT_KEYS_TABLE = `
  CREATE TABLE IF NOT EXISTS agent_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    key_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'ed25519',
    description TEXT,
    is_active TEXT NOT NULL DEFAULT 'true',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
  )
`;

export const CREATE_AGENTS_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_agents_domain ON agents(domain)
`;

export const CREATE_AGENT_KEYS_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_agent_keys_agent_id ON agent_keys(agent_id)
`;

export const CREATE_AGENT_KEYS_KEY_ID_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_agent_keys_key_id ON agent_keys(key_id)
`;