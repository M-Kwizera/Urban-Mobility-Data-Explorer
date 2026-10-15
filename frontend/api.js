const API_BASE = "http://localhost:5000/api";

async function fetchAPI(endpoint, params = {}) {
    const url = new URL(`${API_BASE}${endpoint}`);
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== "") {
            url.searchParams.append(key, params[key]);
        }
    });

    try {
        const response = await fetch(url);
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API Fetch Error:", error);
        throw error;
    }
}