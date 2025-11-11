import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { AgentKeyCreateSchema } from "../models/schemas.js";
import { agentQueries, keyQueries } from "../db/database.js";
import type { AgentKey, Agent } from "../types/index.js";

const keys = new Hono();

/**
 * GET /keys/:key_id
 * Get key by key_id only
 */
keys.get("/:key_id", (c) => {
  try {
    const keyId = c.req.param("key_id");
    const key = keyQueries.getByKeyId.get(keyId) as AgentKey | undefined;
    console.log(key);
    
    if (!key) {
      console.log(`❌ Key not found for ID: ${keyId}`);
      return c.json(
        { success: false, message: `Key not found for ID: ${keyId}` },
        404
      );
    }

    if (key.is_active !== "true") {
      console.log(`❌ Key inactive for ID: ${keyId}`);
      return c.json(
        { success: false, message: `Key is inactive for ID: ${keyId}` },
        404
      );
    }

    // Get associated agent info
    const agent = agentQueries.getById.get(key.agent_id) as Agent | undefined;

    console.log(
      `✅ Retrieved key '${keyId}' (agent: ${agent?.name || "unknown"})`
    );

    return c.json({
      key_id: key.key_id,
      is_active: key.is_active,
      public_key: key.public_key,
      algorithm: key.algorithm,
      description: key.description,
      agent_id: key.agent_id,
      agent_name: agent?.name || null,
      agent_domain: agent?.domain || null,
    });
  } catch (error: any) {
    console.error("❌ Error retrieving key:", error);
    return c.json(
      { success: false, message: `Failed to retrieve key: ${error.message}` },
      500
    );
  }
});

/**
 * GET /agents/:agent_id/keys/:key_id
 * Get specific key for an agent
 */
keys.get("/agents/:agent_id/keys/:key_id", (c) => {
  try {
    const agentId = parseInt(c.req.param("agent_id"));
    const keyId = c.req.param("key_id");

    if (isNaN(agentId)) {
      return c.json({ success: false, message: "Invalid agent ID" }, 400);
    }

    const agent = agentQueries.getById.get(agentId) as Agent | undefined;

    if (!agent) {
      return c.json(
        { success: false, message: `Agent not found for ID: ${agentId}` },
        404
      );
    }

    if (agent.is_active !== "true") {
      return c.json(
        { success: false, message: `Agent is inactive for ID: ${agentId}` },
        404
      );
    }

    const key = keyQueries.getByAgentAndKeyId.get(agentId, keyId) as
      | AgentKey
      | undefined;

    if (!key) {
      return c.json(
        {
          success: false,
          message: `Key '${keyId}' not found for agent ${agentId}`,
        },
        404
      );
    }

    if (key.is_active !== "true") {
      return c.json(
        {
          success: false,
          message: `Key '${keyId}' is inactive for agent ${agentId}`,
        },
        404
      );
    }

    console.log(`✅ Retrieved key '${keyId}' for agent ID: ${agentId}`);

    return c.json({
      agent_id: agentId,
      agent_name: agent.name,
      agent_domain: agent.domain,
      key_id: key.key_id,
      is_active: key.is_active,
      public_key: key.public_key,
      algorithm: key.algorithm,
      description: key.description,
    });
  } catch (error: any) {
    console.error("❌ Error retrieving agent key:", error);
    return c.json(
      {
        success: false,
        message: `Failed to retrieve agent key: ${error.message}`,
      },
      500
    );
  }
});

/**
 * POST /agents/:agent_id/keys
 * Add new key to agent
 */
keys.post(
  "/agents/:agent_id/keys",
  zValidator("json", AgentKeyCreateSchema),
  async (c) => {
    try {
      const agentId = parseInt(c.req.param("agent_id"));
      const body = c.req.valid("json");

      if (isNaN(agentId)) {
        return c.json({ success: false, message: "Invalid agent ID" }, 400);
      }

      const agent = agentQueries.getById.get(agentId) as Agent | undefined;

      if (!agent) {
        return c.json(
          { success: false, message: `Agent not found for ID: ${agentId}` },
          404
        );
      }

      // Check if key_id already exists
      const existingKey = keyQueries.getByAgentAndKeyId.get(
        agentId,
        body.key_id
      );

      if (existingKey) {
        return c.json(
          {
            success: false,
            message: `Key '${body.key_id}' already exists for agent ${agentId}`,
          },
          400
        );
      }

      // Create new key
      const result = keyQueries.create.run(
        agentId,
        body.key_id,
        body.public_key,
        body.algorithm,
        body.description || null,
        body.is_active
      );

      const newKey = keyQueries.getByAgentAndKeyId.get(
        agentId,
        body.key_id
      ) as AgentKey;

      console.log(`✅ Added key '${body.key_id}' to agent ID: ${agentId}`);

      return c.json({
        success: true,
        message: `Key '${body.key_id}' added to agent ${agentId}`,
        key: newKey,
      });
    } catch (error: any) {
      console.error("❌ Error adding agent key:", error);
      return c.json(
        {
          success: false,
          message: `Failed to add agent key: ${error.message}`,
        },
        500
      );
    }
  }
);

export default keys;
