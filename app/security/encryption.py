import os
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from flask import current_app

class EncryptionManager:
    """
    Manages AES-256 encryption for documents using a master key and organization-specific salt.
    """

    @staticmethod
    def _get_derived_key(organization_id: int) -> bytes:
        """
        Derives a unique 32-byte (256-bit) key for the organization using the MASTER_KEY.
        Uses HKDF or simple SHA-256 hashing of (MasterKey + OrgID) for deterministic key derivation.
        Here we use SHA-256 for simplicity and speed, ensuring 256-bit key.
        """
        master_key = os.environ.get("MASTER_KEY")
        if not master_key:
            raise RuntimeError("MASTER_KEY environment variable is not set.")
        
        # Combine master key and organization ID to create a unique key context
        key_material = f"{master_key}:{organization_id}".encode("utf-8")
        return hashlib.sha256(key_material).digest()

    @staticmethod
    def encrypt_file(file_data: bytes, organization_id: int) -> tuple[bytes, bytes]:
        """
        Encrypts bytes using AES-256-GCM.
        Returns (encrypted_data, nonce).
        The nonce is needed for decryption and should be stored or prepended.
        """
        key = EncryptionManager._get_derived_key(organization_id)
        
        # Generate a random 12-byte nonce for GCM
        nonce = os.urandom(12)
        
        # AES-GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(file_data) + encryptor.finalize()
        
        # Return nonce + ciphertext + tag (tag is automatically handled by GCM in some libs, 
        # but in cryptography primitives, finalize() produces the ciphertext, and we get tag separately)
        # Actually in `cryptography`, `finalize()` returns the rest of ciphertext. 
        # The tag is available via `encryptor.tag`.
        
        return nonce + encryptor.tag + ciphertext

    @staticmethod
    def decrypt_file(encrypted_data_with_meta: bytes, organization_id: int) -> bytes:
        """
        Decrypts bytes using AES-256-GCM.
        Expects input format: [Nonce (12)][Tag (16)][Ciphertext]
        """
        key = EncryptionManager._get_derived_key(organization_id)
        
        if len(encrypted_data_with_meta) < 28:
            raise ValueError("Invalid encrypted data format")

        nonce = encrypted_data_with_meta[:12]
        tag = encrypted_data_with_meta[12:28]
        ciphertext = encrypted_data_with_meta[28:]
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        return decryptor.update(ciphertext) + decryptor.finalize()

    @staticmethod
    def get_file_hash(file_data: bytes) -> str:
        """
        Returns SHA-256 hash of the original file for integrity verification.
        """
        return hashlib.sha256(file_data).hexdigest()
