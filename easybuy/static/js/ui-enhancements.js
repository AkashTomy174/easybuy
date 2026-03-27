/**
 * UI/UX Enhancement Scripts
 * Handles loading states, animations, and responsive behaviors
 */

// ============================================================================
// LOADING STATE MANAGEMENT
// ============================================================================

class LoadingManager {
    constructor() {
        this.activeRequests = 0;
        this.loadingContainer = document.getElementById('loading-container');
    }

    /**
     * Show global loading state
     */
    show(message = 'Processing your request...') {
        if (this.loadingContainer) {
            const textElement = this.loadingContainer.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
            this.loadingContainer.classList.remove('hidden');
        }
        this.activeRequests++;
    }

    /**
     * Hide global loading state
     */
    hide() {
        this.activeRequests = Math.max(0, this.activeRequests - 1);
        if (this.activeRequests === 0 && this.loadingContainer) {
            this.loadingContainer.classList.add('hidden');
        }
    }

    /**
     * Show loading state on a specific element
     */
    showOnElement(element) {
        if (!element) return;
        element.classList.add('btn-loading');
        element.disabled = true;
    }

    /**
     * Hide loading state on a specific element
     */
    hideOnElement(element) {
        if (!element) return;
        element.classList.remove('btn-loading');
        element.disabled = false;
    }

    /**
     * Execute function with loading state
     */
    async withLoading(fn, element = null, message = 'Processing...') {
        try {
            if (element) {
                this.showOnElement(element);
            } else {
                this.show(message);
            }

            const result = await fn();
            return result;
        } finally {
            if (element) {
                this.hideOnElement(element);
            } else {
                this.hide();
            }
        }
    }
}

// Global loading manager instance
window.loadingManager = new LoadingManager();

// ============================================================================
// FORM VALIDATION & FEEDBACK
// ============================================================================

class FormValidator {
    constructor(formElement) {
        this.form = formElement;
        this.fields = new Map();
        this.init();
    }

    init() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            this.fields.set(input, {
                element: input,
                messages: {
                    error: '',
                    success: ''
                }
            });

            // Add validation feedback on blur
            input.addEventListener('blur', () => this.validateField(input));
            
            // Clear error on input
            input.addEventListener('input', () => {
                if (input.classList.contains('error')) {
                    this.clearFieldError(input);
                }
            });
        });
    }

    /**
     * Validate a single field
     */
    validateField(field) {
        // Check required
        if (field.hasAttribute('required') && !field.value.trim()) {
            this.showError(field, 'This field is required');
            return false;
        }

        // Check email
        if (field.type === 'email' && field.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                this.showError(field, 'Please enter a valid email address');
                return false;
            }
        }

        // Check phone
        if (field.type === 'tel' && field.value.trim()) {
            const phoneRegex = /^[0-9]{10}$/;
            if (!phoneRegex.test(field.value.replace(/\D/g, ''))) {
                this.showError(field, 'Please enter a valid phone number');
                return false;
            }
        }

        // Check number
        if (field.type === 'number') {
            if (field.hasAttribute('min') && Number(field.value) < Number(field.getAttribute('min'))) {
                this.showError(field, `Must be at least ${field.getAttribute('min')}`);
                return false;
            }
            if (field.hasAttribute('max') && Number(field.value) > Number(field.getAttribute('max'))) {
                this.showError(field, `Must not exceed ${field.getAttribute('max')}`);
                return false;
            }
        }

        this.showSuccess(field);
        return true;
    }

    /**
     * Show error for a field
     */
    showError(field, message) {
        field.classList.remove('success');
        field.classList.add('error');

        const existingError = field.parentElement.querySelector('.form-error');
        if (existingError) {
            existingError.remove();
        }

        const errorEl = document.createElement('div');
        errorEl.className = 'form-error';
        errorEl.textContent = message;
        field.parentElement.appendChild(errorEl);
    }

    /**
     * Show success for a field
     */
    showSuccess(field) {
        field.classList.remove('error');
        field.classList.add('success');

        const existingMessages = field.parentElement.querySelectorAll('.form-error, .form-success');
        existingMessages.forEach(el => el.remove());
    }

    /**
     * Clear error for a field
     */
    clearFieldError(field) {
        field.classList.remove('error');
        const error = field.parentElement.querySelector('.form-error');
        if (error) error.remove();
    }

    /**
     * Validate entire form
     */
    validateForm() {
        let isValid = true;
        this.fields.forEach((_, field) => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        return isValid;
    }

    /**
     * Reset form validation
     */
    reset() {
        this.fields.forEach((_, field) => {
            field.classList.remove('error', 'success');
            const messages = field.parentElement.querySelectorAll('.form-error, .form-success');
            messages.forEach(msg => msg.remove());
        });
    }
}

// ============================================================================
// ANIMATION UTILITIES
// ============================================================================

/**
 * Add fade-in animation to element
 */
function fadeIn(element, duration = 300) {
    element.classList.add('fade-in');
    element.style.animationDuration = `${duration}ms`;
}

/**
 * Add fade-in-up animation to element
 */
function fadeInUp(element, duration = 300) {
    element.classList.add('fade-in-up');
    element.style.animationDuration = `${duration}ms`;
}

/**
 * Add slide-in animation to element
 */
function slideIn(element, direction = 'up', duration = 300) {
    const animationClass = `slide-in-${direction}`;
    element.classList.add(animationClass);
    element.style.animationDuration = `${duration}ms`;
}

/**
 * Add stagger animation to list of elements
 */
function staggerElements(container, baseDelay = 50) {
    const elements = container.querySelectorAll('.stagger-item');
    elements.forEach((el, index) => {
        el.style.animationDelay = `${index * baseDelay}ms`;
    });
}

// ============================================================================
// PAGE TRANSITIONS
// ============================================================================

/**
 * Show page with enter animation
 */
function pageEnter(element) {
    element.classList.add('page-enter');
}

/**
 * Hide page with exit animation
 */
function pageExit(element) {
    element.classList.add('page-exit');
    return new Promise(resolve => {
        setTimeout(resolve, 300);
    });
}

// ============================================================================
// FETCH WITH LOADING STATE
// ============================================================================

/**
 * Fetch with automatic loading state management
 */
async function fetchWithLoading(url, options = {}, element = null) {
    const message = options.message || 'Loading...';
    
    try {
        if (element) {
            window.loadingManager.showOnElement(element);
        } else {
            window.loadingManager.show(message);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    } finally {
        if (element) {
            window.loadingManager.hideOnElement(element);
        } else {
            window.loadingManager.hide();
        }
    }
}

// ============================================================================
// NOTIFICATION/TOAST MANAGER
// ============================================================================

class ToastManager {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-6 right-6 max-w-sm p-4 rounded-lg shadow-lg toast-enter z-50`;
        
        // Set styling based on type
        switch (type) {
            case 'success':
                toast.style.backgroundColor = '#10b981';
                break;
            case 'error':
                toast.style.backgroundColor = '#ef4444';
                break;
            case 'warning':
                toast.style.backgroundColor = '#f59e0b';
                break;
            default:
                toast.style.backgroundColor = '#3b82f6';
        }

        toast.style.color = 'white';
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('toast-enter');
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    static success(message, duration = 3000) {
        this.show(message, 'success', duration);
    }

    static error(message, duration = 4000) {
        this.show(message, 'error', duration);
    }

    static warning(message, duration = 3500) {
        this.show(message, 'warning', duration);
    }

    static info(message, duration = 3000) {
        this.show(message, 'info', duration);
    }
}

window.ToastManager = ToastManager;

// ============================================================================
// RESPONSIVE BEHAVIOR
// ============================================================================

/**
 * Handle responsive breakpoint changes
 */
const mediaQueryList = window.matchMedia('(max-width: 768px)');

function handleMobileChange(e) {
    if (e.matches) {
        // Mobile
        document.documentElement.style.setProperty('--is-mobile', 'true');
    } else {
        // Desktop
        document.documentElement.style.setProperty('--is-mobile', 'false');
    }
}

mediaQueryList.addEventListener('change', handleMobileChange);
handleMobileChange(mediaQueryList);

// ============================================================================
// BUTTON FEEDBACK
// ============================================================================

/**
 * Add ripple effect to button click
 */
function addRippleEffect(button) {
    button.addEventListener('click', function (e) {
        const rect = this.getBoundingClientRect();
        const ripple = document.createElement('span');
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.backgroundColor = 'rgba(255, 255, 255, 0.6)';
        ripple.style.width = ripple.style.height = '20px';
        ripple.style.left = (e.clientX - rect.left - 10) + 'px';
        ripple.style.top = (e.clientY - rect.top - 10) + 'px';
        ripple.style.pointerEvents = 'none';
        ripple.style.animation = 'ripple 0.6s ease-out';

        this.style.position = 'relative';
        this.style.overflow = 'hidden';
        this.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    });
}

// ============================================================================
// AUTO-INIT ON DOCUMENT READY
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize stagger animations for list items with stagger-item class
    const staggerContainers = document.querySelectorAll('[data-stagger]');
    staggerContainers.forEach(container => {
        staggerElements(container);
    });

    // Link CSS key frame animation for ripple effect
    if (!document.querySelector('#ripple-styles')) {
        const style = document.createElement('style');
        style.id = 'ripple-styles';
        style.innerHTML = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
});

// ============================================================================
// EXPORT FOR USE IN TEMPLATES
// ============================================================================

window.FormValidator = FormValidator;
window.fadeIn = fadeIn;
window.fadeInUp = fadeInUp;
window.slideIn = slideIn;
window.staggerElements = staggerElements;
window.pageEnter = pageEnter;
window.pageExit = pageExit;
window.fetchWithLoading = fetchWithLoading;

/**
 * Toggle stock notification for out-of-stock products
 */
function toggleStockNotify(variantId, buttonElement) {
    fetch(`/stock-notify/${variantId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Toggle icon and state
            const icon = buttonElement.querySelector('span.material-symbols-outlined');
            if (data.notified) {
                // Now notified - change to active/filled
                icon.textContent = 'notifications';
                buttonElement.style.background = 'linear-gradient(to right, #059669, #047857)';
                buttonElement.style.boxShadow = '0 4px 12px rgba(6, 78, 59, 0.4)';
                if (typeof ToastManager !== 'undefined') {
                    ToastManager.success(data.message);
                }
            } else {
                // Notification turned off - inactive state
                icon.textContent = 'notifications_off';
                buttonElement.style.background = 'linear-gradient(to right, #6b7280, #4b5563)';
                buttonElement.style.boxShadow = '0 2px 8px rgba(75, 85, 99, 0.3)';
                if (typeof ToastManager !== 'undefined') {
                    ToastManager.info(data.message);
                }
            }
        } else {
            if (typeof ToastManager !== 'undefined') {
                ToastManager.error(data.error || 'Something went wrong');
            }
        }
    })
    .catch(error => {
        console.error('Error toggling stock notification:', error);
        if (typeof ToastManager !== 'undefined') {
            ToastManager.error('Failed to toggle notification');
        }
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
