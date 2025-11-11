# Agent Registry Service

Sample service for managing TAP (Trusted Agent Protocol) agents and their public keys, demonstrating RFC 9421 signature verification.

## Installation

```bash
# Install dependencies (from root directory)  
bun install

# Initialize sample database
cd agent-registry
python populate_sample_data.py

# Start service
bun run dev
```

Access the service at http://localhost:8080 (docs at /docs)

## Key Features

- **Algorithm Support** - Ed25519 public keys
- **Agent Management** - CRUD operations for TAP agents  
- **Key Validation** - Automatic key format validation
- **Registry UI** - Simple web interface for agent management

## Sample API Endpoints

### Agent Management
- `GET /agents` - List all registered agents
- `POST /agents/register` - Register new agent with public key
- `GET /agents/{agent_id}` - Get agent details by agent ID
- `PUT /agents/{agent_id}` - Update agent information
- `DELETE /agents/{agent_id}` - Deactivate agent

### Key Management
- `POST /agents/{agent_id}/keys` - Add new key to existing agent
- `GET /agents/{agent_id}/keys/{key_id}` - Get specific key for agent
- `GET /keys/{key_id}` - **Get key by key ID only (used by CDN proxy)**

### Domain Lookup
- `GET /agents/domain/{domain}` - Find agent by domain

## Key Management

The Agent Registry supports multiple keys per agent, enabling key rotation and multi-algorithm support.

### Adding Keys to Agents

#### 1. Register Agent with Initial Key
```bash
curl -X POST http://localhost:8080/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Payment Directory",
    "domain": "https://directory.example.com",
    "public_key": "4LhKd577EeQdSSrLfnq43RfxG4VofDe3HuwNuoR8szLt",
    "algorithm": "ed25519",
    "key_id": "primary-ed25519",
    "description": "Primary ed25519 key"
  }'
```

#### 2. Add Additional Keys
```bash
curl -X POST http://localhost:8080/agents/1/keys \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "backup-ed25519",
    "algorithm": "ed25519", 
    "public_key": "4LhKd577EeQdSSrLfnq43RfxG4VofDe3HuwNuoR8szLt",
    "description": "Backup Ed25519 key",
    "is_active": "true"
  }'
```

#### 3. CDN Proxy Key Lookup
The CDN proxy uses the `/keys/{key_id}` endpoint to retrieve keys for signature verification:
```bash
curl http://localhost:8080/keys/primary-ed25519
```

Returns:
```json
{
  "key_id": "primary-ed25519",
  "is_active": "true",
  "public_key": "4LhKd577EeQdSSrLfnq43RfxG4VofDe3HuwNuoR8szLt",
  "algorithm": "ed25519",
  "description": "Primary ed25519 key",
  "agent_id": 1,
  "agent_name": "Sample Payment Directory",
  "agent_domain": "https://directory.example.com"
}
```

### Supported Key Formats

#### Ed25519 Keys
- **Format**: Base58 encoded raw public key (44 characters)
- **Example**: `"4LhKd577EeQdSSrLfnq43RfxG4VofDe3HuwNuoR8szLt"`
- **Algorithm**: `"ed25519"`

 
## Architecture

This sample demonstrates:
- Hono service patterns 
- Multi-key agent management
- Public key validation and management
- RFC 9421 compliance for signature verification
- CDN proxy integration patterns

## Registry UI

Access the web interface at http://localhost:8080/ui for:
- Viewing registered agents
- Adding new agents through forms
- Testing agent registration flow


 
