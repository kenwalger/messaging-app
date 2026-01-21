/**
 * Health check service for backend connectivity.
 * 
 * References:
 * - API Contracts (#10)
 * 
 * Provides health check functionality to verify backend availability.
 * Used for development logging only - no UI exposure.
 */

/**
 * Check backend health status.
 * 
 * Calls GET /health endpoint to verify backend availability.
 * 
 * @param apiBaseUrl API base URL (e.g., "http://127.0.0.1:8000")
 * @returns Promise resolving to true if backend is healthy, false otherwise
 */
export async function checkHealth(apiBaseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`, {
      method: 'GET',
    })

    if (!response.ok) {
      return false
    }

    const data = await response.json()
    return data.status === 'healthy'
  } catch (error) {
    // Network errors - backend unavailable
    return false
  }
}
