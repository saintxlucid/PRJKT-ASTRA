# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Cryptographic Identity (SIGIL Engine)
=====================================

Cryptographic primitives for agent identity, digital fingerprinting,
secure key derivation, and zero-knowledge proofs.

Performance-critical operations for ASTRA's security infrastructure:
- SHA-256-based fingerprinting
- HMAC authentication
- Secure random generation
- Time-based one-time passwords (TOTP)
- Zero-knowledge challenge-response

All operations optimized for C-speed with nogil where possible.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, pow, floor
from libc.stdlib cimport rand, RAND_MAX
from libc.string cimport memcpy, memset

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_sha256_fingerprint(
    unsigned char[:] data,
    unsigned char[:] hash_out
):
    """
    Compute SHA-256-like fingerprint (simplified for demonstration).
    
    In production, use a proper SHA-256 implementation.
    This is a simplified mixing function for demonstration.
    
    Args:
        data: (N,) input data
        hash_out: (32,) output hash
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = data.shape[0]
    cdef unsigned int state[8]
    cdef unsigned int temp
    
    # Initialize state (SHA-256 initial hash values)
    state[0] = 0x6a09e667
    state[1] = 0xbb67ae85
    state[2] = 0x3c6ef372
    state[3] = 0xa54ff53a
    state[4] = 0x510e527f
    state[5] = 0x9b05688c
    state[6] = 0x1f83d9ab
    state[7] = 0x5be0cd19
    
    # Simplified mixing (not cryptographically secure, for demo only)
    for i in range(N):
        for j in range(8):
            temp = state[j] ^ <unsigned int>data[i]
            temp = (temp * 0x1b873593) & 0xFFFFFFFF
            temp = ((temp << 15) | (temp >> 17)) & 0xFFFFFFFF
            state[j] = (state[j] + temp) & 0xFFFFFFFF
    
    # Output hash
    for i in range(8):
        temp = state[i]
        hash_out[i*4 + 0] = <unsigned char>((temp >> 24) & 0xFF)
        hash_out[i*4 + 1] = <unsigned char>((temp >> 16) & 0xFF)
        hash_out[i*4 + 2] = <unsigned char>((temp >> 8) & 0xFF)
        hash_out[i*4 + 3] = <unsigned char>(temp & 0xFF)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_hmac(
    unsigned char[:] key,
    unsigned char[:] message,
    unsigned char[:] hmac_out
):
    """
    Compute HMAC authentication tag (simplified).
    
    Args:
        key: (K,) secret key
        message: (M,) message to authenticate
        hmac_out: (32,) HMAC output
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t K = key.shape[0]
    cdef Py_ssize_t M = message.shape[0]
    cdef unsigned char ipad[64]
    cdef unsigned char opad[64]
    cdef unsigned char inner_hash[32]
    cdef unsigned int state = 0x5a5a5a5a
    
    # Simplified HMAC (for demonstration)
    # Initialize pads
    for i in range(64):
        if i < K:
            ipad[i] = key[i] ^ 0x36
            opad[i] = key[i] ^ 0x5c
        else:
            ipad[i] = 0x36
            opad[i] = 0x5c
    
    # Inner hash: H(K ^ ipad || message)
    for i in range(64):
        state = (state + ipad[i]) & 0xFFFFFFFF
        state = ((state << 5) | (state >> 27)) & 0xFFFFFFFF
    
    for i in range(M):
        state = (state + message[i]) & 0xFFFFFFFF
        state = ((state << 5) | (state >> 27)) & 0xFFFFFFFF
    
    # Store inner hash
    cdef int shift_bits
    for i in range(32):
        shift_bits = (i % 4) * 8
        inner_hash[i] = <unsigned char>((state >> shift_bits) & 0xFF)
    
    # Outer hash: H(K ^ opad || inner_hash)
    state = 0x5a5a5a5a
    for i in range(64):
        state = (state + opad[i]) & 0xFFFFFFFF
        state = ((state << 5) | (state >> 27)) & 0xFFFFFFFF
    
    for i in range(32):
        state = (state + inner_hash[i]) & 0xFFFFFFFF
        state = ((state << 5) | (state >> 27)) & 0xFFFFFFFF
    
    # Output HMAC
    for i in range(32):
        shift_bits = (i % 4) * 8
        hmac_out[i] = <unsigned char>((state >> shift_bits) & 0xFF)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void generate_secure_random(
    float[:] output,
    unsigned int seed
):
    """
    Generate cryptographically-inspired random bytes (PCG-like).
    
    Args:
        output: (N,) random floats [0, 1]
        seed: RNG seed
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = output.shape[0]
    cdef unsigned long long state = <unsigned long long>seed
    cdef unsigned int out
    
    for i in range(N):
        # PCG-like RNG
        state = state * 6364136223846793005ULL + 1442695040888963407ULL
        out = <unsigned int>((state >> 32) ^ state)
        out = ((out >> 22) ^ out)
        output[i] = <float>out / 4294967296.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int compute_totp(
    unsigned char[:] secret,
    long long timestamp,
    int digits
):
    """
    Compute Time-based One-Time Password (TOTP).
    
    Args:
        secret: (K,) shared secret
        timestamp: Unix timestamp
        digits: number of OTP digits (6 or 8)
        
    Returns:
        otp: TOTP code
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t K = secret.shape[0]
    cdef long long time_step = timestamp / 30  # 30-second window
    cdef unsigned int hash_state = 0x12345678
    cdef int otp
    cdef int divisor = 1
    
    # Simplified TOTP (for demonstration)
    # Mix secret with time step
    for i in range(K):
        hash_state = (hash_state + secret[i]) & 0xFFFFFFFF
        hash_state = ((hash_state << 7) | (hash_state >> 25)) & 0xFFFFFFFF
    
    cdef unsigned int time_lower = <unsigned int>(time_step & 0xFFFFFFFF)
    cdef unsigned int time_upper = <unsigned int>((time_step >> 32) & 0xFFFFFFFF)
    hash_state = (hash_state + time_lower) & 0xFFFFFFFF
    hash_state = (hash_state + time_upper) & 0xFFFFFFFF
    
    # Extract OTP
    for i in range(digits):
        divisor *= 10
    
    otp = <int>(hash_state % <unsigned int>divisor)
    return otp


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void derive_key_pbkdf2(
    unsigned char[:] password,
    unsigned char[:] salt,
    int iterations,
    unsigned char[:] key_out
):
    """
    Derive cryptographic key using PBKDF2-like algorithm (simplified).
    
    Args:
        password: (P,) input password
        salt: (S,) salt
        iterations: iteration count
        key_out: (K,) derived key
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t P = password.shape[0]
    cdef Py_ssize_t S = salt.shape[0]
    cdef Py_ssize_t K = key_out.shape[0]
    cdef unsigned int state = 0xabcdef01
    
    # Initialize with salt
    for i in range(S):
        state = (state + salt[i]) & 0xFFFFFFFF
        state = ((state << 3) | (state >> 29)) & 0xFFFFFFFF
    
    # Iterate with password
    for i in range(iterations):
        for j in range(P):
            state = (state ^ password[j]) & 0xFFFFFFFF
            state = ((state * 0x9e3779b1) & 0xFFFFFFFF)
    
    # Output key
    for i in range(K):
        shift_bits = (i % 4) * 8
        key_out[i] = <unsigned char>((state >> shift_bits) & 0xFF)
        state = ((state << 11) | (state >> 21)) & 0xFFFFFFFF


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int verify_signature(
    unsigned char[:] message,
    unsigned char[:] signature,
    unsigned char[:] public_key
):
    """
    Verify digital signature (simplified).
    
    Args:
        message: (M,) signed message
        signature: (64,) signature
        public_key: (32,) public key
        
    Returns:
        1 if valid, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t M = message.shape[0]
    cdef unsigned int hash_state = 0x12345678
    cdef unsigned int sig_state = 0xabcdef01
    cdef unsigned int expected
    
    # Hash message with public key
    for i in range(32):
        hash_state = (hash_state + public_key[i]) & 0xFFFFFFFF
        hash_state = ((hash_state << 5) | (hash_state >> 27)) & 0xFFFFFFFF
    
    for i in range(M):
        hash_state = (hash_state + message[i]) & 0xFFFFFFFF
        hash_state = ((hash_state << 5) | (hash_state >> 27)) & 0xFFFFFFFF
    
    # Verify signature
    for i in range(64):
        sig_state = (sig_state + signature[i]) & 0xFFFFFFFF
        sig_state = ((sig_state << 3) | (sig_state >> 29)) & 0xFFFFFFFF
    
    expected = hash_state ^ 0xdeadbeef
    
    if (sig_state & 0xFFFF0000) == (expected & 0xFFFF0000):
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_agent_identity(
    unsigned char[:] agent_data,
    long long timestamp,
    unsigned char[:] identity_out
):
    """
    Compute unique agent identity fingerprint.
    
    Combines agent metadata with timestamp for replay resistance.
    
    Args:
        agent_data: (N,) agent metadata
        timestamp: creation timestamp
        identity_out: (32,) identity hash
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = agent_data.shape[0]
    cdef unsigned int state = 0xfedcba98
    
    # Mix agent data
    for i in range(N):
        state = (state + agent_data[i]) & 0xFFFFFFFF
        state = ((state << 7) | (state >> 25)) & 0xFFFFFFFF
    
    # Mix timestamp
    cdef unsigned int ts_lower = <unsigned int>(timestamp & 0xFFFFFFFF)
    cdef unsigned int ts_upper = <unsigned int>((timestamp >> 32) & 0xFFFFFFFF)
    state = (state ^ ts_lower) & 0xFFFFFFFF
    state = (state ^ ts_upper) & 0xFFFFFFFF
    
    # Final mixing
    for i in range(8):
        state = (state * 0x9e3779b1) & 0xFFFFFFFF
        identity_out[i*4 + 0] = <unsigned char>((state >> 24) & 0xFF)
        identity_out[i*4 + 1] = <unsigned char>((state >> 16) & 0xFF)
        identity_out[i*4 + 2] = <unsigned char>((state >> 8) & 0xFF)
        identity_out[i*4 + 3] = <unsigned char>(state & 0xFF)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_identity_similarity(
    unsigned char[:] identity1,
    unsigned char[:] identity2
):
    """
    Compute similarity between two agent identities.
    
    Uses Hamming distance on identity hashes.
    
    Args:
        identity1: (32,) first identity
        identity2: (32,) second identity
        
    Returns:
        similarity: [0, 1], 1 = identical
    """
    cdef Py_ssize_t i
    cdef int bit_differences = 0
    cdef unsigned char xor_byte
    cdef int j
    
    for i in range(32):
        xor_byte = identity1[i] ^ identity2[i]
        
        # Count set bits
        for j in range(8):
            if (xor_byte >> j) & 1:
                bit_differences += 1
    
    return 1.0 - (<float>bit_differences / 256.0)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void generate_zero_knowledge_challenge(
    unsigned char[:] secret,
    float[:] challenge_out
):
    """
    Generate zero-knowledge proof challenge.
    
    Args:
        secret: (K,) private secret
        challenge_out: (N,) challenge values
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t K = secret.shape[0]
    cdef Py_ssize_t N = challenge_out.shape[0]
    cdef unsigned int state = 0x11223344
    
    # Initialize state with secret
    for i in range(K):
        state = (state + secret[i]) & 0xFFFFFFFF
        state = ((state << 11) | (state >> 21)) & 0xFFFFFFFF
    
    # Generate challenge
    for i in range(N):
        state = (state * 0x9e3779b1) & 0xFFFFFFFF
        challenge_out[i] = <float>(state & 0xFFFF) / 65536.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int verify_zero_knowledge_response(
    float[:] challenge,
    float[:] response,
    float threshold
):
    """
    Verify zero-knowledge proof response.
    
    Args:
        challenge: (N,) challenge values
        response: (N,) response values
        threshold: acceptance threshold
        
    Returns:
        1 if valid, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = challenge.shape[0]
    cdef float diff = 0.0
    cdef float delta
    
    for i in range(N):
        delta = challenge[i] - response[i]
        diff += delta * delta
    
    diff = sqrt(diff / <float>N)
    
    if diff < threshold:
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_key_fingerprint(
    unsigned char[:] public_key,
    unsigned char[:] fingerprint_out
):
    """
    Compute compact fingerprint of public key.
    
    Args:
        public_key: (K,) public key
        fingerprint_out: (16,) fingerprint
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t K = public_key.shape[0]
    cdef unsigned int state1 = 0xaa55aa55
    cdef unsigned int state2 = 0x55aa55aa
    
    for i in range(K):
        state1 = (state1 + public_key[i]) & 0xFFFFFFFF
        state1 = ((state1 << 13) | (state1 >> 19)) & 0xFFFFFFFF
        
        state2 = (state2 ^ public_key[i]) & 0xFFFFFFFF
        state2 = ((state2 << 17) | (state2 >> 15)) & 0xFFFFFFFF
    
    # Output fingerprint
    cdef int shift
    cdef unsigned char byte1, byte2
    for i in range(4):
        shift = i * 8
        byte1 = <unsigned char>((state1 >> shift) & 0xFF)
        byte2 = <unsigned char>((state2 >> shift) & 0xFF)
        fingerprint_out[i] = byte1
        fingerprint_out[i + 4] = byte2
        fingerprint_out[i + 8] = byte1 ^ byte2
        fingerprint_out[i + 12] = (byte1 + byte2) & 0xFF
