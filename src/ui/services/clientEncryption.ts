/**
 * Client-side encryption utility for POC.
 * 
 * ⚠️ POC-SAFE ONLY: This is NOT production-grade encryption.
 * 
 * Requirements:
 * - Deterministic (same input produces same output for testing)
 * - Uses Web Crypto API
 * - Produces base64-encoded output
 * - Symmetric key (hardcoded or derived per device for now)
 * 
 * Approach:
 * - AES-GCM encryption
 * - Static key seeded from device_id
 * - Base64-encoded output
 */

/**
 * Encrypt plaintext message using client-side encryption.
 * 
 * Uses AES-GCM with a key derived from device_id.
 * Output is base64-encoded for backend compatibility.
 * 
 * @param plaintext Plaintext message to encrypt
 * @param deviceId Device ID used to derive encryption key
 * @returns Promise resolving to base64-encoded encrypted payload
 * @throws Error if encryption fails
 */
export async function encryptMessage(
  plaintext: string,
  deviceId: string
): Promise<string> {
  try {
    // Derive encryption key from device_id (deterministic for POC)
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(deviceId.padEnd(32, '0').slice(0, 32)), // 32 bytes for AES-256
      { name: 'PBKDF2' },
      false,
      ['deriveKey']
    )

    // Derive AES-GCM key
    const key = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: new TextEncoder().encode('aam-poc-salt'), // Static salt for POC
        iterations: 1000, // Low iteration count for POC performance
        hash: 'SHA-256',
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt']
    )

    // Generate IV (12 bytes for AES-GCM)
    const iv = crypto.getRandomValues(new Uint8Array(12))

    // Encrypt plaintext
    const plaintextBytes = new TextEncoder().encode(plaintext)
    const encryptedData = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv: iv,
      },
      key,
      plaintextBytes
    )

    // Combine IV and encrypted data
    const combined = new Uint8Array(iv.length + encryptedData.byteLength)
    combined.set(iv, 0)
    combined.set(new Uint8Array(encryptedData), iv.length)

    // Encode as base64
    // Use a more efficient method for large arrays
    let binary = ''
    const len = combined.length
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(combined[i])
    }
    const base64 = btoa(binary)
    
    // Log for diagnostics (POC only)
    if (import.meta.env.DEV) {
      console.log('[Encryption] Mode: client, Payload type: encrypted, Success: true')
    }

    return base64
  } catch (error) {
    // Log encryption failure
    if (import.meta.env.DEV) {
      console.error('[Encryption] Mode: client, Payload type: plaintext, Success: false', error)
    }
    throw new Error(`Message could not be encrypted. Not sent. ${error instanceof Error ? error.message : String(error)}`)
  }
}

/**
 * Check if Web Crypto API is available.
 * 
 * @returns True if Web Crypto API is available
 */
export function isEncryptionAvailable(): boolean {
  return typeof crypto !== 'undefined' && 
         typeof crypto.subtle !== 'undefined' &&
         typeof crypto.subtle.encrypt === 'function'
}
