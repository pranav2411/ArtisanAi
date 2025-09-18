/**
 * Main JavaScript File
 * Initializes the application and sets up common functionality
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initThemeSwitcher();
    initMobileMenu();
    initDropdowns();
    initModals();
    initForms();
    initFlashMessages();
    
    // Initialize any page-specific scripts
    if (typeof initPage !== 'undefined') {
        initPage();
    }
});

/**
 * Theme Switcher
 * Toggles between light and dark theme
 */
function initThemeSwitcher() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;
    
    // Check for saved theme preference or use system preference
    const savedTheme = localStorage.getItem(AppConfig.STORAGE_KEYS.THEME) || 'system';
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Apply the saved theme or system preference
    if (savedTheme === 'dark' || (savedTheme === 'system' && prefersDark)) {
        html.classList.add('dark');
        if (themeIcon) themeIcon.classList.replace('fa-moon', 'fa-sun');
    } else {
        html.classList.remove('dark');
        if (themeIcon) themeIcon.classList.replace('fa-sun', 'fa-moon');
    }
    
    // Toggle theme when the button is clicked
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = html.classList.contains('dark');
            const newTheme = isDark ? 'light' : 'dark';
            
            // Toggle the dark class on the html element
            html.classList.toggle('dark');
            
            // Update the icon
            if (themeIcon) {
                themeIcon.classList.toggle('fa-moon');
                themeIcon.classList.toggle('fa-sun');
            }
            
            // Save the preference
            localStorage.setItem(AppConfig.STORAGE_KEYS.THEME, newTheme);
            
            // Dispatch a custom event for other components to listen to
            document.dispatchEvent(new CustomEvent('themeChange', { detail: { theme: newTheme } }));
        });
    }
}

/**
 * Mobile Menu Toggle
 * Handles showing/hiding the mobile menu
 */
function initMobileMenu() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
            mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
            mobileMenu.classList.toggle('hidden');
        });
    }
}

/**
 * Dropdown Menus
 * Handles showing/hiding dropdown menus
 */
function initDropdowns() {
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        const dropdowns = document.querySelectorAll('[data-dropdown]');
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('[data-dropdown-toggle]');
            const menu = dropdown.querySelector('[data-dropdown-menu]');
            
            if (!dropdown.contains(e.target) && !e.target.matches('[data-dropdown-toggle]')) {
                menu.classList.add('hidden');
                toggle?.setAttribute('aria-expanded', 'false');
            }
        });
    });
    
    // Toggle dropdown menus
    document.querySelectorAll('[data-dropdown-toggle]').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = toggle.closest('[data-dropdown]');
            const menu = dropdown?.querySelector('[data-dropdown-menu]');
            
            if (menu) {
                const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
                toggle.setAttribute('aria-expanded', !isExpanded);
                menu.classList.toggle('hidden');
                
                // Close other open dropdowns
                document.querySelectorAll('[data-dropdown]').forEach(otherDropdown => {
                    if (otherDropdown !== dropdown) {
                        const otherMenu = otherDropdown.querySelector('[data-dropdown-menu]');
                        const otherToggle = otherDropdown.querySelector('[data-dropdown-toggle]');
                        if (otherMenu && otherToggle) {
                            otherMenu.classList.add('hidden');
                            otherToggle.setAttribute('aria-expanded', 'false');
                        }
                    }
                });
            }
        });
    });
}

/**
 * Modal Dialogs
 * Handles showing/hiding modal dialogs
 */
function initModals() {
    // Close modals when clicking the close button or outside the modal
    document.addEventListener('click', (e) => {
        // Close button
        if (e.target.closest('[data-modal-hide]')) {
            const modalId = e.target.closest('[data-modal-hide]').getAttribute('data-modal-hide');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('hidden');
                document.body.classList.remove('overflow-hidden');
            }
        }
        
        // Click outside modal content
        if (e.target.matches('[data-modal]')) {
            e.target.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }
    });
    
    // Show modal when trigger is clicked
    document.querySelectorAll('[data-modal-toggle]').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const modalId = toggle.getAttribute('data-modal-toggle');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove('hidden');
                document.body.classList.add('overflow-hidden');
                
                // Focus on the first focusable element
                const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (focusable) focusable.focus();
            }
        });
    });
}

/**
 * Form Handling
 * Handles form submission and validation
 */
function initForms() {
    document.querySelectorAll('form[data-ajax]').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitButton = form.querySelector('[type="submit"]');
            const originalButtonText = submitButton?.innerHTML;
            const formData = new FormData(form);
            const action = form.getAttribute('action') || window.location.href;
            const method = form.getAttribute('method') || 'POST';
            
            // Disable submit button and show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
            }
            
            try {
                const response = await fetch(action, {
                    method,
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    // Handle successful form submission
                    if (result.redirect) {
                        window.location.href = result.redirect;
                    } else if (result.message) {
                        showFlashMessage(result.message, 'success');
                        form.reset();
                    }
                } else {
                    // Handle form errors
                    if (result.errors) {
                        showFormErrors(form, result.errors);
                    } else if (result.message) {
                        showFlashMessage(result.message, 'error');
                    }
                }
            } catch (error) {
                console.error('Form submission error:', error);
                showFlashMessage('An error occurred. Please try again.', 'error');
            } finally {
                // Re-enable submit button and restore original text
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                }
            }
        });
    });
    
    // Real-time form validation
    document.querySelectorAll('form [data-validate]').forEach(input => {
        input.addEventListener('input', () => {
            validateField(input);
        });
        
        input.addEventListener('blur', () => {
            validateField(input);
        });
    });
}

/**
 * Validate a single form field
 */
function validateField(field) {
    const value = field.value.trim();
    const fieldName = field.getAttribute('name') || field.getAttribute('id');
    const errorElement = document.getElementById(`${fieldName}-error`);
    
    // Reset error state
    field.classList.remove('border-red-500');
    if (errorElement) {
        errorElement.textContent = '';
    }
    
    // Required validation
    if (field.required && !value) {
        showFieldError(field, errorElement, 'This field is required');
        return false;
    }
    
    // Email validation
    if (field.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        showFieldError(field, errorElement, 'Please enter a valid email address');
        return false;
    }
    
    // Password strength validation
    if (field.type === 'password' && field.dataset.validate === 'password' && value.length < 8) {
        showFieldError(field, errorElement, 'Password must be at least 8 characters long');
        return false;
    }
    
    return true;
}

/**
 * Show error message for a form field
 */
function showFieldError(field, errorElement, message) {
    field.classList.add('border-red-500');
    if (errorElement) {
        errorElement.textContent = message;
    }
}

/**
 * Show form errors
 */
function showFormErrors(form, errors) {
    Object.entries(errors).forEach(([fieldName, messages]) => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        const errorElement = document.getElementById(`${fieldName}-error`) || 
                           field?.closest('.form-group')?.querySelector('.error-message');
        
        if (field && errorElement) {
            field.classList.add('border-red-500');
            errorElement.textContent = Array.isArray(messages) ? messages[0] : messages;
        }
    });
}

/**
 * Flash Messages
 * Handles displaying flash messages to the user
 */
function initFlashMessages() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.flash-message').forEach(message => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        });
    }, 5000);
    
    // Close button for flash messages
    document.querySelectorAll('.flash-close').forEach(button => {
        button.addEventListener('click', (e) => {
            const message = e.target.closest('.flash-message');
            if (message) {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }
        });
    });
}

/**
 * Show a flash message
 * @param {string} message - The message to display
 * @param {string} type - The type of message (success, error, warning, info)
 * @param {number} duration - How long to display the message in milliseconds (default: 5000)
 */
function showFlashMessage(message, type = 'info', duration = 5000) {
    const container = document.getElementById('flash-messages') || document.body;
    const messageId = `flash-${Date.now()}`;
    const icon = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    const messageElement = document.createElement('div');
    messageElement.id = messageId;
    messageElement.className = `flash-message flash-${type} fixed top-4 right-4 z-50 flex items-center p-4 mb-4 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out`;
    messageElement.role = 'alert';
    messageElement.innerHTML = `
        <i class="fas ${icon} text-lg mr-3"></i>
        <span class="flex-1">${message}</span>
        <button type="button" class="flash-close ml-4 text-xl" aria-label="Close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(messageElement);
    
    // Trigger reflow to enable the transition
    messageElement.offsetHeight;
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            const element = document.getElementById(messageId);
            if (element) {
                element.style.opacity = '0';
                setTimeout(() => element.remove(), 300);
            }
        }, duration);
    }
    
    // Return the message element in case we need to manually remove it
    return messageElement;
}

// Make showFlashMessage available globally
window.showFlashMessage = showFlashMessage;
