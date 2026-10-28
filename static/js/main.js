// Main JavaScript file for Student Result Processing System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.classList.remove('show');
            setTimeout(function() {
                alert.remove();
            }, 150);
        }, 5000);
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Ask before any action that carries a data-confirm message
    document.querySelectorAll('[data-confirm]').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(button.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Stop a second click from submitting a form twice
    document.querySelectorAll('form[data-single-submit]').forEach(function(form) {
        form.addEventListener('submit', function() {
            form.querySelectorAll('button[type="submit"]').forEach(function(button) {
                setTimeout(function() { button.disabled = true; }, 0);
            });
        });
    });

    // Light/dark switch; theme.js applied the saved choice before the page painted
    document.querySelectorAll('[data-theme-toggle]').forEach(function(button) {
        const root = document.documentElement;
        const sync = function() {
            button.setAttribute('aria-pressed', root.getAttribute('data-bs-theme') === 'dark');
        };
        sync();
        button.addEventListener('click', function() {
            const next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-bs-theme', next);
            try { localStorage.setItem('srps-theme', next); } catch (e) { /* storage blocked: lasts until reload */ }
            sync();
        });
    });

    // Print buttons (inline handlers are blocked by the content security policy)
    document.querySelectorAll('[data-print]').forEach(function(button) {
        button.addEventListener('click', function() { window.print(); });
    });

    // Form validation helper
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
});

// Function to validate marks input
function validateMarks(marksObtained, maximumMarks) {
    marksObtained = parseFloat(marksObtained);
    maximumMarks = parseFloat(maximumMarks);
    
    if (isNaN(marksObtained) || isNaN(maximumMarks)) {
        return { valid: false, message: 'Please enter valid numbers' };
    }
    
    if (marksObtained < 0) {
        return { valid: false, message: 'Marks obtained cannot be negative' };
    }
    
    if (maximumMarks <= 0) {
        return { valid: false, message: 'Maximum marks must be greater than zero' };
    }
    
    if (marksObtained > maximumMarks) {
        return { valid: false, message: 'Marks obtained cannot exceed maximum marks' };
    }
    
    return { valid: true };
}

// Function to format percentage
function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

// Function to get grade class
function getGradeClass(grade) {
    return 'grade-' + grade.replace('+', '');
}

// Function to get pass status class
function getPassStatusClass(status) {
    return 'pass-' + status;
}
