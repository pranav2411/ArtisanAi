/**
 * API Client
 * A wrapper around fetch to handle API requests consistently
 */

class ApiClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
    }

    /**
     * Set the authentication token
     * @param {string} token - The authentication token
     */
    setAuthToken(token) {
        if (token) {
            this.defaultHeaders['Authorization'] = `Bearer ${token}`;
        } else {
            delete this.defaultHeaders['Authorization'];
        }
    }

    /**
     * Make an HTTP request
     * @private
     */
    async _fetch(method, endpoint, data = null, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = { ...this.defaultHeaders, ...options.headers };
        
        // Handle FormData (for file uploads)
        let body;
        if (data instanceof FormData) {
            // Remove Content-Type header to let the browser set it with the correct boundary
            delete headers['Content-Type'];
            body = data;
        } else if (data) {
            body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, {
                method,
                headers,
                body,
                credentials: 'same-origin',
                ...options
            });

            // Handle 401 Unauthorized (token expired)
            if (response.status === 401) {
                // You might want to handle token refresh here
                console.error('Authentication required');
                // Redirect to login or refresh token
                window.location.href = '/auth/login?redirect=' + encodeURIComponent(window.location.pathname);
                return;
            }

            // Parse JSON response
            const responseData = await response.json().catch(() => ({}));

            if (!response.ok) {
                const error = new Error(responseData.message || 'Something went wrong');
                error.status = response.status;
                error.data = responseData;
                throw error;
            }

            return responseData;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    // HTTP Methods
    get(endpoint, params = {}, options = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this._fetch('GET', url, null, options);
    }

    post(endpoint, data = {}, options = {}) {
        return this._fetch('POST', endpoint, data, options);
    }

    put(endpoint, data = {}, options = {}) {
        return this._fetch('PUT', endpoint, data, options);
    }

    patch(endpoint, data = {}, options = {}) {
        return this._fetch('PATCH', endpoint, data, options);
    }

    delete(endpoint, data = null, options = {}) {
        return this._fetch('DELETE', endpoint, data, options);
    }

    // File Upload
    upload(endpoint, file, fieldName = 'file', data = {}) {
        const formData = new FormData();
        
        // Add the file
        formData.append(fieldName, file);
        
        // Add any additional data
        Object.entries(data).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                formData.append(key, value);
            }
        });
        
        return this.post(endpoint, formData, {
            headers: {
                // Let the browser set the Content-Type with the correct boundary
                ...this.defaultHeaders,
                'Content-Type': undefined
            }
        });
    }
}

// Create a singleton instance
const api = new ApiClient(AppConfig.API_BASE_URL);

// Set up auth token from localStorage if available
const token = localStorage.getItem('auth_token');
if (token) {
    api.setAuthToken(token);
}

// Make api available globally
window.api = api;

export default api;
