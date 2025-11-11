# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import re
import time
import json
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
import base58

# Example Ed25519 public key in Base58 format (32 bytes encoded)
# In production, replace with actual public key
publicKeyBase58 = "4LhKd577EeQdSSrLfnq43RfxG4VofDe3HuwNuoR8szLt"

class SignatureVerifier:
    def __init__(self):
        # In production, these would be loaded from secure storage/config
        self.trusted_agents = {
            "https://directory.example.com": {
                "public_key": self._load_public_key("example"),
                "name": "Example Directory"
            },
            "https://payment.sample.org": {
                "public_key": self._load_public_key("sample"),
                "name": "Sample Payment Directory"
            }
        }
    
    def _load_public_key(self, agent_name: str):
        """Load Ed25519 public key from Base58 string. In production, load from secure storage."""
        
        if agent_name == "example":
            # Decode Base58 to get 32-byte Ed25519 public key
            public_key_bytes = base58.b58decode(publicKeyBase58)
            if len(public_key_bytes) != 32:
                raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(public_key_bytes)}")
            return ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        elif agent_name == "sample":
            # Replace with actual sample public key in production
            public_key_bytes = base58.b58decode(publicKeyBase58)
            if len(public_key_bytes) != 32:
                raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(public_key_bytes)}")
            return ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        else:
            raise ValueError(f"Unknown agent name: {agent_name}")

    
    def parse_signature_headers(self, signature_agent: str, signature_input: str, signature: str) -> Optional[Dict]:
        """Parse the signature headers and extract components."""
        try:
            # Parse Signature-Agent
            agent_url = signature_agent.strip('"')
            
            # Parse Signature-Input (Ed25519 only)
            signature_input_pattern = r'sig1=\("([^"]+)"\);\s*nonce="([^"]+)";\s*created=(\d+);\s*expires=(\d+);\s*keyid="([^"]+)";\s*tag="([^"]+)"'
            match = re.match(signature_input_pattern, signature_input.strip())
            
            if not match:
                return None
            
            signature_params, nonce, created, expires, keyid, tag = match.groups()
            
            # Parse Signature (Base58 format)
            signature_pattern = r'sig1=:([^:]+):'
            sig_match = re.match(signature_pattern, signature.strip())
            
            if not sig_match:
                return None
            
            signature_value = sig_match.group(1)
            
            return {
                "agent_url": agent_url,
                "signature_params": signature_params.split(" "),
                "nonce": nonce,
                "created": int(created),
                "expires": int(expires),
                "keyid": keyid,
                "tag": tag,
                "signature": signature_value
            }
        except Exception as e:
            print(f"Error parsing signature headers: {e}")
            return None
    
    def verify_signature(self, parsed_data: Dict, request_data: Dict) -> Tuple[bool, str]:
        """Verify the Ed25519 signature against the request data."""
        try:
            agent_url = parsed_data["agent_url"]
            
            # Check if agent is trusted
            if agent_url not in self.trusted_agents:
                return False, f"Unknown agent: {agent_url}"
            
            # Check timestamp validity
            current_time = int(time.time())
            if current_time < parsed_data["created"]:
                return False, "Signature created in the future"
            
            if current_time > parsed_data["expires"]:
                return False, "Signature expired"
            
            # Build signature string
            signature_string = self._build_signature_string(
                parsed_data["signature_params"],
                request_data,
                parsed_data["nonce"],
                parsed_data["created"],
                parsed_data["expires"]
            )
            
            # Verify Ed25519 signature
            public_key = self.trusted_agents[agent_url]["public_key"]
            
            # Decode Base58 signature to bytes
            signature_bytes = base58.b58decode(parsed_data["signature"])
            
            # Ed25519 signatures should be exactly 64 bytes
            if len(signature_bytes) != 64:
                return False, f"Ed25519 signature must be 64 bytes, got {len(signature_bytes)}"
            
            try:
                # Ed25519 verification (no hashing needed, pure signature)
                public_key.verify(
                    signature_bytes,
                    signature_string.encode('utf-8')
                )
                return True, f"Verified agent: {self.trusted_agents[agent_url]['name']}"
            except InvalidSignature:
                return False, "Invalid Ed25519 signature"
                
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def _build_signature_string(self, params: list, request_data: Dict, nonce: str, created: int, expires: int) -> str:
        """Build the signature string from the parameters."""
        signature_parts = []
        
        for param in params:
            if param == "@authority":
                signature_parts.append(f'"@authority": "{request_data.get("authority", "")}"')
            elif param == "@path":
                signature_parts.append(f'"@path": "{request_data.get("path", "")}"')
            elif param == "directory-agent":
                signature_parts.append(f'"directory-agent": "{request_data.get("directory-agent", "")}"')
            elif param == "query-param":
                signature_parts.append(f'"query-param": "{request_data.get("query-param", "")}"')
        
        signature_parts.extend([
            f'"nonce": "{nonce}"',
            f'"created": {created}',
            f'"expires": {expires}'
        ])
        
        return "\n".join(signature_parts)
    
    def is_trusted_agent(self, signature_agent: str, signature_input: str, signature: str, request_data: Dict) -> Tuple[bool, str]:
        """Main method to verify if the request is from a trusted agent."""
        # Parse headers
        parsed_data = self.parse_signature_headers(signature_agent, signature_input, signature)
        
        if not parsed_data:
            return False, "Invalid signature format"
        
        # Verify signature
        return self.verify_signature(parsed_data, request_data)

# Global instance
signature_verifier = SignatureVerifier()