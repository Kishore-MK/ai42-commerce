import { z } from 'zod';
import { validateEd25519PublicKey } from '../utils/crypto.js';

// Custom validation for Ed25519 base58 public keys
const ed25519Base58Key = z.string()
  .min(32, 'Public key too short')
  .max(64, 'Public key too long')
  .refine(
    (key) => validateEd25519PublicKey(key),
    'Invalid Ed25519 base58 public key - must be 32 bytes encoded in base58'
  );

// Agent Key schemas
export const AgentKeyCreateSchema = z.object({
  key_id: z.string().min(1).max(100),
  public_key: ed25519Base58Key,
  algorithm: z.literal('ed25519'),
  description: z.string().max(1000).optional().nullable(),
  is_active: z.enum(['true', 'false']).default('true'),
});

export const AgentKeyUpdateSchema = z.object({
  key_id: z.string().min(1).max(100).optional(),
  public_key: ed25519Base58Key.optional(),
  algorithm: z.literal('ed25519').optional(),
  description: z.string().max(1000).optional().nullable(),
  is_active: z.enum(['true', 'false']).optional(),
});

// Agent schemas
export const AgentCreateSchema = z.object({
  name: z.string().min(1).max(255),
  domain: z.string()
    .min(1)
    .max(255)
    .refine(
      (domain) => domain.startsWith('http://') || domain.startsWith('https://'),
      'Domain must start with http:// or https://'
    ),
  description: z.string().max(1000).optional().nullable(),
  contact_email: z.string().email().max(255).optional().nullable(),
  is_active: z.enum(['true', 'false']).default('true'),
  keys: z.array(AgentKeyCreateSchema).default([]),
});

export const AgentUpdateSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  description: z.string().max(1000).optional().nullable(),
  contact_email: z.string().email().max(255).optional().nullable(),
  is_active: z.enum(['true', 'false']).optional(),
});

// Type exports
export type AgentKeyCreate = z.infer<typeof AgentKeyCreateSchema>;
export type AgentKeyUpdate = z.infer<typeof AgentKeyUpdateSchema>;
export type AgentCreate = z.infer<typeof AgentCreateSchema>;
export type AgentUpdate = z.infer<typeof AgentUpdateSchema>;