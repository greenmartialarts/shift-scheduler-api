/**
 * SchedulerAPI SDK
 * A lightweight, zero-dependency client for the Volunteer Scheduler API.
 */
class SchedulerAPI {
    /**
     * @param {string} apiKey - Your HMAC API Key
     * @param {string} baseUrl - The base URL of the API (default: live production)
     */
    constructor(apiKey, baseUrl = "https://shift-scheduler-api-3nxm.vercel.app") {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
    }

    /**
     * Internal helper for making requests
     */
    async _request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            Authorization: `Bearer ${this.apiKey}`,
            ...options.headers,
        };

        const response = await fetch(url, { ...options, headers });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Request failed with status ${response.status}`);
        }

        return response.json();
    }

    /**
     * Generate a schedule based on JSON input
     * @param {Object} data - {volunteers, unassigned_shifts, current_assignments}
     */
    async schedule(data) {
        return this._request("/api/schedule", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
    }

    /**
     * Validate schedule input without running the engine
     * @param {Object} data - {volunteers, unassigned_shifts, current_assignments}
     */
    async validate(data) {
        return this._request("/api/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
    }

    /**
     * Get usage statistics for the current API key
     */
    async getUsage() {
        return this._request("/api/usage");
    }

    /**
     * Upload CSV files and generate a schedule
     * @param {File|Blob} volunteersFile
     * @param {File|Blob} shiftsFile
     * @param {File|Blob} [assignmentsFile]
     */
    async scheduleCSV(volunteersFile, shiftsFile, assignmentsFile = null) {
        const formData = new FormData();
        formData.append("volunteers_file", volunteersFile);
        formData.append("shifts_file", shiftsFile);
        if (assignmentsFile) {
            formData.append("assignments_file", assignmentsFile);
        }

        return this._request("/api/schedule/csv", {
            method: "POST",
            body: formData,
        });
    }
}

// Export for various environments
if (typeof module !== "undefined" && module.exports) {
    module.exports = SchedulerAPI;
} else if (typeof window !== "undefined") {
    window.SchedulerAPI = SchedulerAPI;
}
