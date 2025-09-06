#!/usr/bin/env python3
"""
Script to extract RSA public key components and update LTI config
"""

import os
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def extract_jwk_components():
    """Extract modulus and exponent from our RSA public key"""
    try:
        # Path to our public key
        keys_dir = os.path.join(os.path.dirname(__file__), 'keys')
        public_key_path = os.path.join(keys_dir, 'public.key')
        
        if not os.path.exists(public_key_path):
            print("❌ Public key not found. Please run the LTI service first to generate keys.")
            return None
        
        # Load the public key
        with open(public_key_path, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())
        
        # Extract modulus and exponent
        public_numbers = public_key.public_numbers()
        modulus = public_numbers.n
        exponent = public_numbers.e
        
        # Convert to base64url encoding (remove padding)
        n_bytes = modulus.to_bytes((modulus.bit_length() + 7) // 8, byteorder='big')
        n_b64 = base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('=')
        
        e_bytes = exponent.to_bytes((exponent.bit_length() + 7) // 8, byteorder='big')
        e_b64 = base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
        
        # Generate key ID (same as in LTI service)
        import hashlib
        key_id = hashlib.sha256(str(modulus).encode()).hexdigest()[:16]
        
        print(f"✅ Extracted JWK components:")
        print(f"  - Key ID: {key_id}")
        print(f"  - Modulus (n): {n_b64}")
        print(f"  - Exponent (e): {e_b64}")
        
        return {
            'kid': key_id,
            'n': n_b64,
            'e': e_b64
        }
        
    except Exception as e:
        print(f"❌ Error extracting JWK components: {e}")
        return None

def update_lti_config(jwk_components):
    """Update the LTI config with actual JWK components"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'lti-tool-config.json')
        
        # Read current config
        with open(config_path, 'r') as f:
            config = f.read()
        
        # Replace placeholders with actual values
        config = config.replace('"REPLACE_WITH_ACTUAL_MODULUS"', f'"{jwk_components["n"]}"')
        config = config.replace('"REPLACE_WITH_ACTUAL_EXPONENT"', f'"{jwk_components["e"]}"')
        config = config.replace('"595e5313f5423dfb"', f'"{jwk_components["kid"]}"')
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.write(config)
        
        print(f"✅ Updated LTI config with actual JWK components")
        
    except Exception as e:
        print(f"❌ Error updating LTI config: {e}")

if __name__ == "__main__":
    print("🔑 Extracting JWK components from RSA public key...")
    
    jwk_components = extract_jwk_components()
    if jwk_components:
        update_lti_config(jwk_components)
        print("\n🎯 Next steps:")
        print("1. Copy the updated lti-tool-config.json content")
        print("2. Paste it into Canvas Developer Keys")
        print("3. Try the AI Tutor button again")
    else:
        print("\n❌ Failed to extract JWK components") 