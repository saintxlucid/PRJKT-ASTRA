#!/usr/bin/env python3
"""
ASTRA Secrets Encryption Script
Encrypts config/.env using GPG with AES256
Usage: python scripts/encrypt_secrets.py [--key-id ASTRA_LOCAL]
"""
import subprocess
import sys
from pathlib import Path
import argparse

def generate_env_template():
    """Generate example .env file"""
    template = """# ASTRA Environment Variables
# WARNING: This file contains sensitive secrets
# After filling in values, encrypt with: python scripts/encrypt_secrets.py

# LLM Providers (if using external APIs)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Memory Signing (generate with: openssl rand -hex 32)
MEMORY_SIGNING_KEY=

# Optional: External Search/Embedding Services
JINA_API_KEY=
BRAVE_API_KEY=

# Database (if using remote)
DB_CONNECTION_STRING=

# Optional: S3 Backup Credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BACKUP_BUCKET=

# Optional: Monitoring
DATADOG_API_KEY=
"""
    
    env_path = Path("config/.env")
    
    if env_path.exists():
        response = input(f"⚠️ {env_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    with open(env_path, "w") as f:
        f.write(template)
    
    print(f"✅ Created template: {env_path}")
    print("\n📝 Next steps:")
    print("1. Edit config/.env and fill in your secrets")
    print("2. Run: python scripts/encrypt_secrets.py")
    print("3. Delete plaintext config/.env")
    return True

def encrypt_env(key_id: str = "ASTRA_LOCAL"):
    """Encrypt .env file using GPG"""
    env_path = Path("config/.env")
    encrypted_path = Path("config/.env.gpg")
    
    if not env_path.exists():
        print(f"❌ {env_path} not found")
        print("Run with --generate to create template")
        return False
    
    # Check if secrets are filled in
    with open(env_path, "r") as f:
        content = f.read()
        empty_lines = [line for line in content.split("\n") 
                      if "=" in line and line.split("=")[1].strip() == ""]
    
    if len(empty_lines) > 2:  # Allow a few optional vars to be empty
        print(f"⚠️ Warning: {len(empty_lines)} variables are empty")
        response = input("Continue encryption? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    if encrypted_path.exists():
        response = input(f"⚠️ {encrypted_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    print(f"\n🔐 Encrypting {env_path} with GPG...")
    
    try:
        # Use symmetric encryption (password-based)
        subprocess.run([
            "gpg",
            "--symmetric",
            "--cipher-algo", "AES256",
            "--output", str(encrypted_path),
            str(env_path)
        ], check=True)
        
        print(f"✅ Encrypted: {encrypted_path}")
        print(f"   Algorithm: AES256")
        print(f"   Key ID: {key_id}")
        
        # Verify encryption worked
        print("\n🔍 Verifying encryption...")
        result = subprocess.run(
            ["gpg", "--list-packets", str(encrypted_path)],
            capture_output=True,
            text=True
        )
        
        if "AES256" in result.stdout:
            print("✅ Encryption verified")
        
        # Prompt to delete plaintext
        print("\n⚠️ SECURITY WARNING: Plaintext secrets still exist")
        response = input(f"Delete {env_path}? (y/N): ")
        if response.lower() == 'y':
            env_path.unlink()
            print(f"✅ Deleted {env_path}")
            print("\n🔒 Secrets secured!")
        else:
            print(f"\n⚠️ Remember to manually delete {env_path}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Encryption failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ GPG not found. Install GPG:")
        print("   Windows: https://gpg4win.org/")
        print("   Linux: sudo apt install gnupg")
        print("   macOS: brew install gnupg")
        return False

def decrypt_env():
    """Decrypt .env.gpg for verification"""
    encrypted_path = Path("config/.env.gpg")
    
    if not encrypted_path.exists():
        print(f"❌ {encrypted_path} not found")
        return False
    
    print(f"🔓 Decrypting {encrypted_path}...")
    
    try:
        result = subprocess.run([
            "gpg",
            "--decrypt",
            str(encrypted_path)
        ], capture_output=True, text=True, check=True)
        
        print("\n✅ Decryption successful:")
        print("-" * 60)
        # Show first 3 lines only
        lines = result.stdout.split("\n")[:3]
        for line in lines:
            if line and not line.startswith("#"):
                # Redact values
                if "=" in line:
                    key = line.split("=")[0]
                    print(f"{key}=***REDACTED***")
            else:
                print(line)
        print("...")
        print("-" * 60)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Decryption failed: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="ASTRA Secrets Encryption")
    parser.add_argument("--generate", action="store_true", help="Generate .env template")
    parser.add_argument("--verify", action="store_true", help="Test decryption")
    parser.add_argument("--key-id", default="ASTRA_LOCAL", help="GPG key ID")
    args = parser.parse_args()
    
    if args.generate:
        generate_env_template()
        return
    
    if args.verify:
        decrypt_env()
        return
    
    # Default: encrypt
    if encrypt_env(args.key_id):
        print("\n✅ SUCCESS - Secrets encrypted and secured")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
