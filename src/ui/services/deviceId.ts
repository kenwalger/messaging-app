/**
 * Device ID generation and persistence utility.
 * 
 * Generates a unique device ID per browser/device and persists it in localStorage.
 * This allows the same device to maintain its identity across page reloads.
 */

const DEVICE_ID_KEY = 'aam_device_id'

/**
 * Generate a new device ID.
 * 
 * Format: device-{timestamp}-{random}
 * 
 * @returns New device ID string
 */
function generateDeviceId(): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 11)
  return `device-${timestamp}-${random}`
}

/**
 * Get or create device ID.
 * 
 * If device ID exists in localStorage, returns it.
 * Otherwise, generates a new one and stores it.
 * 
 * @returns Device ID string
 */
export function getOrCreateDeviceId(): string {
  if (typeof window === 'undefined') {
    // Server-side rendering - return a temporary ID
    return generateDeviceId()
  }

  try {
    const stored = localStorage.getItem(DEVICE_ID_KEY)
    if (stored) {
      return stored
    }

    // Generate new device ID
    const deviceId = generateDeviceId()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
    
    if (import.meta.env.DEV) {
      console.log(`[Device] Generated new device ID: ${deviceId}`)
    }
    
    return deviceId
  } catch (error) {
    // localStorage unavailable (private browsing, etc.) - generate temporary ID
    if (import.meta.env.DEV) {
      console.warn('[Device] localStorage unavailable, using temporary device ID:', error)
    }
    return generateDeviceId()
  }
}

/**
 * Clear stored device ID.
 * 
 * Useful for testing or resetting device identity.
 */
export function clearDeviceId(): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(DEVICE_ID_KEY)
    } catch (error) {
      // Ignore errors
    }
  }
}
