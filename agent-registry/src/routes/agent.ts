import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { AgentCreateSchema, AgentUpdateSchema } from "../models/schemas.js";
import {
  agentQueries,
  keyQueries,
  getAgentWithKeys,
  getAllAgentsWithKeys, 
} from "../db/database.js";
import type { AgentWithKeys } from "../types/index.js";

const agents = new Hono();

/**
 * POST /agents/register
 * Register a new agent or update existing
 */
agents.post("/register", zValidator("json", AgentCreateSchema), async (c) => {
  try {
    const body = c.req.valid("json");

    // Check if agent exists
    const existing = agentQueries.getByDomain.get(body.domain) as
      | AgentWithKeys
      | undefined;

    if (existing) {
      // Update existing agent
      agentQueries.update.run(
        body.name,
        body.description || null,
        body.contact_email || null,
        body.is_active,
        existing.id
      );

      // Handle keys
      if (body.keys && body.keys.length > 0) {
        for (const keyData of body.keys) {
          const existingKey = keyQueries.getByAgentAndKeyId.get(
            existing.id,
            keyData.key_id
          );

          if (existingKey) {
            // Update existing key
            keyQueries.update.run(
              keyData.key_id,
              keyData.public_key,
              keyData.algorithm,
              keyData.description || null,
              keyData.is_active,
              (existingKey as any).id
            );
          } else {
            // Create new key
            keyQueries.create.run(
              existing.id,
              keyData.key_id,
              keyData.public_key,
              keyData.algorithm,
              keyData.description || null,
              keyData.is_active
            );
          }
        }
      }

      const updated = getAgentWithKeys(existing.id);
      console.log(`✅ Updated agent registration for domain: ${body.domain}`);

      return c.json({
        success: true,
        message: `Agent registration updated for domain: ${body.domain}`,
        agent: updated,
      });
    } else {
      // Create new agent
      const result = agentQueries.create.run(
        body.name,
        body.domain,
        body.description || null,
        body.contact_email || null,
        body.is_active
      );

      const agentId = result.lastInsertRowid as number;

      // Add keys
      if (body.keys && body.keys.length > 0) {
        for (const keyData of body.keys) {
          keyQueries.create.run(
            agentId,
            keyData.key_id,
            keyData.public_key,
            keyData.algorithm,
            keyData.description || null,
            keyData.is_active
          );
        }
      }

      const newAgent = getAgentWithKeys(agentId);
      console.log(
        `✅ New agent registered for domain: ${body.domain}, ID: ${agentId}`
      );

      return c.json({
        success: true,
        message: `Agent successfully registered for domain: ${body.domain}, ID: ${agentId}`,
        agent: newAgent,
      });
    }
  } catch (error: any) {
    console.error("❌ Error registering agent:", error);
    return c.json(
      {
        success: false,
        message: `Failed to register agent: ${error.message}`,
      },
      500
    );
  }
});

/**
 * GET /agents
 * List all agents
 */
agents.get("/", (c) => {
  try {
    const activeOnly = c.req.query("active_only") !== "false";
    const agents = getAllAgentsWithKeys(activeOnly);

    console.log(`✅ Retrieved ${agents.length} agents`);
    return c.json(agents);
  } catch (error: any) {
    console.error("❌ Error listing agents:", error);
    return c.json(
      { success: false, message: `Failed to list agents: ${error.message}` },
      500
    );
  }
});

/**
 * GET /agents/:id
 * Get agent by ID
 */
agents.get("/:id", (c) => {
  try {
    const agentId = parseInt(c.req.param("id"));

    if (isNaN(agentId)) {
      return c.json({ success: false, message: "Invalid agent ID" }, 400);
    }

    const agent = getAgentWithKeys(agentId);

    if (!agent) {
      console.log(`❌ Agent not found for ID: ${agentId}`);
      return c.json(
        { success: false, message: `Agent not found for ID: ${agentId}` },
        404
      );
    }

    if (agent.is_active !== "true") {
      console.log(`❌ Agent inactive for ID: ${agentId}`);
      return c.json(
        { success: false, message: `Agent is inactive for ID: ${agentId}` },
        404
      );
    }

    console.log(`✅ Retrieved agent info for ID: ${agentId}`);
    return c.json(agent);
  } catch (error: any) {
    console.error("❌ Error retrieving agent:", error);
    return c.json(
      { success: false, message: `Failed to retrieve agent: ${error.message}` },
      500
    );
  }
});

 
/**
 * GET /agents/domain/:domain
 * Get agent by domain (legacy endpoint)
 */
agents.get("/domain/:domain", (c) => {
  try {
    const domain = c.req.param("domain");
    const agent = agentQueries.getByDomain.get(domain) as
      | AgentWithKeys
      | undefined;

    if (!agent) {
      console.log(`❌ Agent not found for domain: ${domain}`);
      return c.json(
        { success: false, message: `Agent not found for domain: ${domain}` },
        404
      );
    }

    if (agent.is_active !== "true") {
      console.log(`❌ Agent inactive for domain: ${domain}`);
      return c.json(
        { success: false, message: `Agent is inactive for domain: ${domain}` },
        404
      );
    }

    const agentWithKeys = getAgentWithKeys(agent.id);
    console.log(`✅ Retrieved agent info for domain: ${domain}`);
    return c.json(agentWithKeys);
  } catch (error: any) {
    console.error("❌ Error retrieving agent:", error);
    return c.json(
      { success: false, message: `Failed to retrieve agent: ${error.message}` },
      500
    );
  }
});

/**
 * PUT /agents/:id
 * Update agent
 */
agents.put("/:id", zValidator("json", AgentUpdateSchema), async (c) => {
  try {
    const agentId = parseInt(c.req.param("id"));
    const body = c.req.valid("json");

    if (isNaN(agentId)) {
      return c.json({ success: false, message: "Invalid agent ID" }, 400);
    }

    const existing = agentQueries.getById.get(agentId) as
      | AgentWithKeys
      | undefined;

    if (!existing) {
      console.log(`❌ Agent not found for ID: ${agentId}`);
      return c.json(
        { success: false, message: `Agent not found for ID: ${agentId}` },
        404
      );
    }

    // Update with provided fields or keep existing
    agentQueries.update.run(
      body.name || existing.name,
      body.description !== undefined ? body.description : existing.description,
      body.contact_email !== undefined
        ? body.contact_email
        : existing.contact_email,
      body.is_active || existing.is_active,
      agentId
    );

    const updated = getAgentWithKeys(agentId);
    console.log(`✅ Updated agent for ID: ${agentId}`);

    return c.json({
      success: true,
      message: `Agent updated for ID: ${agentId}`,
      agent: updated,
    });
  } catch (error: any) {
    console.error("❌ Error updating agent:", error);
    return c.json(
      { success: false, message: `Failed to update agent: ${error.message}` },
      500
    );
  }
});

/**
 * DELETE /agents/:id
 * Deactivate agent (soft delete)
 */
agents.delete("/:id", (c) => {
  try {
    const agentId = parseInt(c.req.param("id"));

    if (isNaN(agentId)) {
      return c.json({ success: false, message: "Invalid agent ID" }, 400);
    }

    const agent = agentQueries.getById.get(agentId);

    if (!agent) {
      console.log(`❌ Agent not found for ID: ${agentId}`);
      return c.json(
        { success: false, message: `Agent not found for ID: ${agentId}` },
        404
      );
    }

    agentQueries.deactivate.run(agentId);
    console.log(`✅ Deactivated agent for ID: ${agentId}`);

    return c.json({
      success: true,
      message: `Agent deactivated for ID: ${agentId}`,
    });
  } catch (error: any) {
    console.error("❌ Error deactivating agent:", error);
    return c.json(
      {
        success: false,
        message: `Failed to deactivate agent: ${error.message}`,
      },
      500
    );
  }
});

export default agents;
