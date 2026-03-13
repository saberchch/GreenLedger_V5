/**
 * Academy Progress Tracker
 * Tracks section views and quiz completion for GreenLedger Academy modules.
 */

class AcademyTracker {
    constructor(moduleId, initialViewedSections = []) {
        this.moduleId = moduleId;
        this.observedSections = new Set(initialViewedSections);
        this.init();
    }

    init() {
        console.log(`[Academy] Tracking started for Module ${this.moduleId}`);
        this.applyInitialProgress();
        this.setupIntersectionObserver();
    }

    applyInitialProgress() {
        // Mark existing sections in UI
        this.observedSections.forEach(sectionId => {
            this.updateSidebarUI(sectionId);
        });

        // Initial progress bar update
        const totalSections = document.querySelectorAll('section[id]').length || 8;
        const percent = Math.min(Math.round((this.observedSections.size / totalSections) * 100), 100);
        this.updateProgressBar(percent);
    }

    setupIntersectionObserver() {
        const options = {
            root: null,
            threshold: 0.3 // Section is considered "viewed" when 30% visible
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const sectionId = entry.target.id;
                    if (!this.observedSections.has(sectionId)) {
                        this.markSectionViewed(sectionId);
                        this.observedSections.add(sectionId);
                    }
                }
            });
        }, options);

        // Observe all sections within the content area
        document.querySelectorAll('section[id]').forEach(section => {
            observer.observe(section);
        });
    }

    async markSectionViewed(sectionId) {
        console.log(`[Academy] Viewing section: ${sectionId}`);
        await this.updateProgress({ section_id: sectionId });

        // Update UI: Mark sidebar link as completed
        this.updateSidebarUI(sectionId);
    }

    updateSidebarUI(sectionId) {
        const sidebarLink = document.querySelector(`aside a[href="#${sectionId}"] span`);
        if (sidebarLink) {
            sidebarLink.classList.remove('bg-primary/30');
            sidebarLink.classList.add('bg-primary', 'shadow-[0_0_8px_rgba(12,168,90,0.5)]');
        }
    }

    async markModuleCompleted(score = null) {
        console.log(`[Academy] Module ${this.moduleId} completed with score: ${score}`);
        const result = await this.updateProgress({ is_completed: true, score: score });

        if (result && result.status === 'success') {
            const feedback = document.getElementById('mastery-feedback');
            if (feedback) {
                feedback.classList.remove('hidden');
                feedback.classList.add('animate-bounce');
            }
            this.updateProgressBar(100);
        }
    }

    async updateProgress(data) {
        try {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

            const response = await fetch('/academy/api/progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    module_id: this.moduleId,
                    ...data
                })
            });

            const result = await response.json();

            if (result && result.viewed_count !== undefined) {
                const totalSections = document.querySelectorAll('section[id]').length || 8;
                const percent = Math.min(Math.round((result.viewed_count / totalSections) * 100), 100);
                this.updateProgressBar(result.is_completed ? 100 : percent);

                if (percent === 100 && !result.is_completed) {
                    // Auto-complete if all sections are viewed
                    this.markModuleCompleted(100);
                }
            }

            return result;
        } catch (error) {
            console.error('[Academy] Failed to update progress:', error);
        }
    }

    updateProgressBar(percent) {
        const bar = document.getElementById('academy-progress-bar');
        const text = document.getElementById('academy-progress-text');
        if (bar) bar.style.width = `${percent}%`;
        if (text) text.innerText = `${percent}% Completed`;
    }
}

// Make globally available
window.AcademyTracker = AcademyTracker;
