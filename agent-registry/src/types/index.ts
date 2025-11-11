export interface Agent {
    id: number;
    name: string;
    domain: string;
    description: string | null;
    contact_email: string | null;
    is_active: string;
    created_at: string;
    updated_at: string;
  }
  
  export interface AgentKey {
    id: number;
    agent_id: number;
    key_id: string;
    public_key: string; // Ed25519 base58 encoded
    algorithm: string; // Always "ed25519"
    description: string | null;
    is_active: string;
    created_at: string;
    updated_at: string;
  }
  
  export interface AgentWithKeys extends Agent {
    keys: AgentKey[];
  }
  
  export interface ApiResponse<T = any> {
    success: boolean;
    message: string;
    data?: T;
  }
  
  export interface AgentResponse extends ApiResponse {
    agent?: AgentWithKeys;
  }
  
  export interface AgentKeyResponse extends ApiResponse {
    key?: AgentKey;
  }