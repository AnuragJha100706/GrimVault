/**
 * DevVault - Core Client-Side Application Scripts
 * Author: Anurag Jha (@AnuragJha100706)
 * Includes: Theme switcher, Chart.js integrations, live search filter,
 * floating toast notifications, and keyboard shortcuts.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Dark / Light Mode
    initThemeManager();

    // 2. Quick Live Search Filter on Projects List
    initQuickFilter();

    // 3. Initialize Bootstrap Tooltips
    initBootstrapHelpers();

    // 4. Keyboard Shortcuts (/ to search, Esc to close)
    initKeyboardShortcuts();
});

/* ==========================================================================
   1. Theme Management (Dark / Light Mode)
   ========================================================================== */
function initThemeManager() {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');
    const htmlEl = document.documentElement;

    const savedTheme = localStorage.getItem('devvault-theme') || 'dark';
    setTheme(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const currentTheme = htmlEl.getAttribute('data-bs-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            localStorage.setItem('devvault-theme', newTheme);
        });
    }

    function setTheme(theme) {
        htmlEl.setAttribute('data-bs-theme', theme);
        htmlEl.className = theme;
        if (themeIcon) {
            if (theme === 'dark') {
                themeIcon.className = 'bi bi-sun-fill text-warning';
                if (themeToggleBtn) themeToggleBtn.setAttribute('title', 'Switch to Light Mode');
            } else {
                themeIcon.className = 'bi bi-moon-stars-fill text-primary';
                if (themeToggleBtn) themeToggleBtn.setAttribute('title', 'Switch to Dark Mode');
            }
        }
        // Notify components (e.g. charts) of theme change
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }
}

/* ==========================================================================
   2. Quick Live Search Filter for Projects
   ========================================================================== */
function initQuickFilter() {
    const quickInput = document.getElementById('quickFilterInput');
    if (!quickInput) return;

    quickInput.addEventListener('input', function () {
        const filterVal = this.value.toLowerCase().trim();
        const projectItems = document.querySelectorAll('.filterable-project-item');

        projectItems.forEach(item => {
            const searchableText = item.getAttribute('data-search') || item.textContent.toLowerCase();
            if (searchableText.includes(filterVal)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

/* ==========================================================================
   3. Bootstrap Helper Initializer
   ========================================================================== */
function initBootstrapHelpers() {
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
}

/* ==========================================================================
   4. Keyboard Shortcuts (/ to search, Esc to dismiss)
   ========================================================================== */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Press '/' to focus quick filter if not inside an input/textarea
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            const quickInput = document.getElementById('quickFilterInput');
            if (quickInput) {
                e.preventDefault();
                quickInput.focus();
                quickInput.select();
            }
        }
    });
}

/* ==========================================================================
   5. Floating Toast Notification System
   ========================================================================== */
window.DevVaultToast = {
    show(message, type = 'success') {
        let container = document.querySelector('.devvault-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'devvault-toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `devvault-toast border-${type}`;

        const iconClass = type === 'success' ? 'bi-check-circle-fill text-success' :
                          type === 'danger' ? 'bi-exclamation-triangle-fill text-danger' :
                          type === 'warning' ? 'bi-exclamation-circle-fill text-warning' : 'bi-info-circle-fill text-info';

        toast.innerHTML = `
            <i class="bi ${iconClass} fs-5"></i>
            <span class="flex-grow-1">${message}</span>
            <button type="button" class="btn-close btn-close-sm" aria-label="Close" style="font-size: 0.65rem;"></button>
        `;

        toast.querySelector('.btn-close').addEventListener('click', () => toast.remove());
        container.appendChild(toast);

        // Auto dismiss after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

/* ==========================================================================
   6. Chart.js Dashboard Visualizations
   ========================================================================== */
window.DevVaultCharts = {
    charts: {},

    refreshAll() {
        const colors = this.getThemeColors();
        Object.values(this.charts).forEach(chart => {
            if (!chart) return;
            if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                chart.options.plugins.legend.labels.color = colors.textColor;
            }
            if (chart.options.scales) {
                if (chart.options.scales.x) {
                    if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = colors.textColor;
                    if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = colors.gridColor;
                }
                if (chart.options.scales.y) {
                    if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = colors.textColor;
                    if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = colors.gridColor;
                }
            }
            chart.update();
        });
    },

    getThemeColors() {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        return {
            textColor: isDark ? '#94a3b8' : '#475569',
            gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
            palette: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#6366f1']
        };
    },

    initStatusDoughnut(canvasId, statusCounts) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === 'undefined') return null;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const colors = this.getThemeColors();
        const labels = Object.keys(statusCounts);
        const data = Object.values(statusCounts);

        const statusColorMap = {
            'Completed': '#10b981',
            'In Progress': '#3b82f6',
            'Idea': '#8b5cf6',
            'On Hold': '#f59e0b',
            'Archived': '#64748b'
        };

        const bgColors = labels.map(label => statusColorMap[label] || '#94a3b8');

        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: bgColors,
                    borderWidth: 2,
                    borderColor: 'transparent',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: colors.textColor,
                            boxWidth: 10,
                            padding: 12,
                            font: { family: 'inherit', size: 11 }
                        }
                    }
                },
                cutout: '70%'
            }
        });
        return this.charts[canvasId];
    },

    initCategoryBar(canvasId, labels, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === 'undefined') return null;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const colors = this.getThemeColors();

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Projects',
                    data: data,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4,
                    maxBarThickness: 32
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, color: colors.textColor },
                        grid: { color: colors.gridColor }
                    },
                    x: {
                        ticks: { color: colors.textColor },
                        grid: { display: false }
                    }
                }
            }
        });
        return this.charts[canvasId];
    },

    initTechHorizontalBar(canvasId, labels, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx || typeof Chart === 'undefined') return null;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const colors = this.getThemeColors();

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Projects',
                    data: data,
                    backgroundColor: '#8b5cf6',
                    borderRadius: 4,
                    maxBarThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, color: colors.textColor },
                        grid: { color: colors.gridColor }
                    },
                    y: {
                        ticks: { color: colors.textColor },
                        grid: { display: false }
                    }
                }
            }
        });
        return this.charts[canvasId];
    }
};

// Global theme change listener to automatically refresh Chart.js themes
window.addEventListener('themeChanged', () => {
    if (window.DevVaultCharts && typeof window.DevVaultCharts.refreshAll === 'function') {
        window.DevVaultCharts.refreshAll();
    }
});
