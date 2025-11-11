import * as anchor from "@coral-xyz/anchor";
import {
  SystemProgram,
  PublicKey,
  Keypair,
} from "@solana/web3.js";
import { BN } from "bn.js";
import fs from "fs";
import nacl from "tweetnacl";
import bs58 from "bs58";
import { idl } from "./idl.js"; // Your agent registry IDL
import { connection, user } from "./secrets.js";

 

const provider = new anchor.AnchorProvider(connection, user, {
  preflightCommitment: "confirmed",
});

anchor.setProvider(provider);
export const program = new anchor.Program(idl, provider);

 

// Helper: Generate random intent hash
export function generateIntentHash() {
  return Array.from(nacl.randomBytes(32));
}
  
export async function verifyIntent(intentPDA) {
  const result = await program.methods
    .verifyIntent()
    .accounts({
      intent: intentPDA,
    })
    .view();

  console.log("✅ Intent verification result:", result);
  return result.isValid;
}
 
export async function updateReputation(
  agentPDA,
  scoreDelta,
  reason,
) {
  const [registryPDA] = PublicKey.findProgramAddressSync(
    [Buffer.from("registry")],
    program.programId
  );

  const tx = await program.methods
    .updateReputation(new BN(scoreDelta), reason)
    .accounts({
      agent: agentPDA,
      registry: registryPDA,
      authority: user.publicKey,
    })
    .signers([user.payer])
    .rpc();

  console.log(`✅ Reputation updated by ${scoreDelta}:`, tx);
}

// 9. Get Agent Score
export async function getAgentScore(agentPDA) {
  const score = await program.methods
    .getAgentScore()
    .accounts({
      agent: agentPDA,
    })
    .view();

  console.log("✅ Agent score:", score.toString());
  return score;
}
 