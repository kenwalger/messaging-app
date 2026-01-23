/**
 * Encryption mode configuration for POC.
 * 
 * Defines encryption mode as a first-class concept in the frontend.
 * This is a POC affordance and should be clearly labeled as such.
 */

export type EncryptionMode = 'client' | 'server'

/**
 * Default encryption mode.
 * 
 * Per requirements: default to 'client' (production mode).
 */
export const DEFAULT_ENCRYPTION_MODE: EncryptionMode = 'client'

/**
 * Encryption mode store/context.
 * 
 * Simple state management for encryption mode.
 * In a production app, this would be managed via proper state management (Redux, Zustand, etc.).
 * For POC, we use a simple module-level state with callbacks.
 */
class EncryptionModeStore {
  private mode: EncryptionMode = DEFAULT_ENCRYPTION_MODE
  private listeners: Set<(mode: EncryptionMode) => void> = new Set()

  /**
   * Get current encryption mode.
   */
  getMode(): EncryptionMode {
    return this.mode
  }

  /**
   * Set encryption mode.
   * 
   * @param mode New encryption mode
   */
  setMode(mode: EncryptionMode): void {
    if (this.mode !== mode) {
      this.mode = mode
      this.notifyListeners()
    }
  }

  /**
   * Subscribe to mode changes.
   * 
   * @param listener Callback when mode changes
   * @returns Unsubscribe function
   */
  subscribe(listener: (mode: EncryptionMode) => void): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.mode))
  }
}

// Singleton instance
export const encryptionModeStore = new EncryptionModeStore()
