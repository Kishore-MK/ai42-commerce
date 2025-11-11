import nacl from 'tweetnacl';
import bs58 from 'bs58';

/**
 * Validates Ed25519 base58 public key
 * @param publicKeyBase58 - Base58 encoded public key
 * @returns true if valid, false otherwise
 */
export function validateEd25519PublicKey(publicKeyBase58: string): boolean {
  try {
    const decoded = bs58.decode(publicKeyBase58);
    // Ed25519 public keys are exactly 32 bytes
    return decoded.length === 32;
  } catch (error) {
    return false;
  }
}

/**
 * Verifies Ed25519 signature
 * @param message - Message that was signed (as Uint8Array)
 * @param signatureBase58 - Base58 encoded signature
 * @param publicKeyBase58 - Base58 encoded public key
 * @returns true if signature is valid
 */
export function verifySignature(
  message: Uint8Array,
  signatureBase58: string,
  publicKeyBase58: string
): boolean {
  try {
    const signature = bs58.decode(signatureBase58);
    const publicKey = bs58.decode(publicKeyBase58);
    
    // Ed25519 signatures are 64 bytes, public keys are 32 bytes
    if (signature.length !== 64 || publicKey.length !== 32) {
      return false;
    }
    
    return nacl.sign.detached.verify(message, signature, publicKey);
  } catch (error) {
    console.error('Signature verification error:', error);
    return false;
  }
}

/**
 * Converts string to Uint8Array for signing/verification
 */
export function stringToUint8Array(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}