/**
 * Frontend Configuration
 * This file contains all the configuration settings for the frontend
 */

const Config = {
    // API Endpoints
    API_BASE_URL: '/api/v1',
    ENDPOINTS: {
        AUTH: {
            LOGIN: '/auth/login',
            REGISTER: '/auth/register',
            LOGOUT: '/auth/logout',
            FORGOT_PASSWORD: '/auth/forgot-password',
            RESET_PASSWORD: '/auth/reset-password',
            VERIFY_EMAIL: '/auth/verify-email',
            ME: '/auth/me'
        },
        PRODUCTS: {
            BASE: '/products',
            SEARCH: '/products/search',
            CATEGORIES: '/products/categories',
            FEATURED: '/products/featured',
            RECOMMENDED: '/products/recommended'
        },
        ORDERS: {
            BASE: '/orders',
            CANCEL: '/orders/cancel',
            TRACK: '/orders/track'
        },
        CART: {
            BASE: '/cart',
            ADD_ITEM: '/cart/items',
            REMOVE_ITEM: '/cart/items',
            UPDATE_QUANTITY: '/cart/items/quantity'
        },
        USERS: {
            PROFILE: '/users/profile',
            ADDRESSES: '/users/addresses',
            PAYMENT_METHODS: '/users/payment-methods',
            NOTIFICATIONS: '/users/notifications',
            WISHLIST: '/users/wishlist'
        },
        ARTISANS: {
            DASHBOARD: '/artisan/dashboard',
            PRODUCTS: '/artisan/products',
            ORDERS: '/artisan/orders',
            ANALYTICS: '/artisan/analytics',
            VERIFICATION: '/artisan/verification'
        },
        AI: {
            GENERATE_DESCRIPTION: '/ai/generate/description',
            GENERATE_IMAGES: '/ai/generate/images',
            ANALYZE_TRENDS: '/ai/analyze/trends',
            PRICE_RECOMMENDATION: '/ai/recommend/price'
        }
    },
    
    // Pagination
    PAGINATION: {
        DEFAULT_PAGE: 1,
        DEFAULT_PER_PAGE: 12,
        MAX_PER_PAGE: 100
    },
    
    // File Upload
    UPLOAD: {
        MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
        ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        MAX_FILES: 10
    },
    
    // Local Storage Keys
    STORAGE_KEYS: {
        AUTH_TOKEN: 'auth_token',
        USER: 'user',
        CART: 'cart',
        THEME: 'theme',
        REDIRECT_AFTER_LOGIN: 'redirect_after_login'
    },
    
    // Theme
    THEMES: {
        LIGHT: 'light',
        DARK: 'dark',
        SYSTEM: 'system'
    },
    
    // Currency
    CURRENCY: {
        SYMBOL: '₹',
        CODE: 'INR',
        DECIMALS: 2,
        FORMAT: 'en-IN'
    },
    
    // Date & Time
    DATE_FORMAT: 'dd/MM/yyyy',
    DATE_TIME_FORMAT: 'dd/MM/yyyy HH:mm',
    
    // Google Maps
    MAPS: {
        API_KEY: '', // Will be set from environment
        DEFAULT_ZOOM: 12,
        DEFAULT_CENTER: { lat: 20.5937, lng: 78.9629 }, // Center of India
        MARKER_ICON: '/static/images/map-marker.png'
    },
    
    // Social Media
    SOCIAL: {
        FACEBOOK: 'https://facebook.com/artisanai',
        INSTAGRAM: 'https://instagram.com/artisanai',
        TWITTER: 'https://twitter.com/artisanai',
        PINTEREST: 'https://pinterest.com/artisanai'
    },
    
    // Feature Flags
    FEATURES: {
        ENABLE_AI: true,
        ENABLE_VERIFICATION: true,
        ENABLE_SOCIAL_LOGIN: true,
        ENABLE_PHONE_VERIFICATION: false
    },
    
    // Initialize the config with environment-specific settings
    init: function() {
        // You can override any config values here based on environment
        // For example, in production:
        // if (window.location.hostname === 'production.example.com') {
        //     this.API_BASE_URL = 'https://api.production.example.com';
        // }
        
        // Load Google Maps API key from meta tag if available
        const mapsApiKeyMeta = document.querySelector('meta[name="google-maps-api-key"]');
        if (mapsApiKeyMeta) {
            this.MAPS.API_KEY = mapsApiKeyMeta.getAttribute('content');
        }
        
        return this;
    }
}.init();

// Make config available globally
window.AppConfig = Config;

export default Config;
