// Mercor Job Market Analysis - Frontend JavaScript

class JobMarketAnalysis {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.tags = {};
        this.stats = {};
        this.charts = {};
        
        this.init();
    }

    async init() {
        await this.loadTags();
        await this.loadStats();
        this.setupEventListeners();
        this.updateHeroStats();
        this.updateCompanyStats();
        this.loadMercorJobs();
        this.initializeCharts();
    }

    async loadTags() {
        try {
            const response = await fetch('/api/tags');
            this.tags = await response.json();
            this.populateTagFilters();
        } catch (error) {
            console.error('Error loading tags:', error);
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            this.stats = await response.json();
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    setupEventListeners() {
        // Tag filter change
        document.getElementById('mercor-skill-filter').addEventListener('change', (e) => {
            this.currentPage = 1;
            this.loadMercorJobs();
        });

        // Search input
        let searchTimeout;
        document.getElementById('mercor-search').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.currentPage = 1;
                this.loadMercorJobs();
            }, 500);
        });

        // Global skill filter
        document.getElementById('skill-filter').addEventListener('change', (e) => {
            this.updateSkillsChart();
        });
    }

    populateTagFilters() {
        const mercorFilter = document.getElementById('mercor-skill-filter');
        const globalFilter = document.getElementById('skill-filter');
        
        Object.entries(this.tags).forEach(([id, name]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = name;
            
            mercorFilter.appendChild(option.cloneNode(true));
            globalFilter.appendChild(option);
        });
    }

    updateHeroStats() {
        const mercorTotal = this.stats.mercor?.total_jobs || 0;
        const competitorTotal = Object.values(this.stats)
            .filter(stat => stat.total_jobs)
            .reduce((sum, stat) => sum + stat.total_jobs, 0) - mercorTotal;

        document.getElementById('total-mercor-jobs').textContent = mercorTotal.toLocaleString();
        document.getElementById('total-competitor-jobs').textContent = competitorTotal.toLocaleString();
    }

    updateCompanyStats() {
        const companies = ['mercor', 'afterquery', 'alignerr', 'handshake', 'outlier'];
        
        companies.forEach(company => {
            const stat = this.stats[company];
            if (stat) {
                // Update total jobs
                const totalElement = document.getElementById(`${company}-total`);
                if (totalElement) {
                    totalElement.textContent = stat.total_jobs.toLocaleString();
                }

                // Update salary
                const salaryElement = document.getElementById(`${company}-salary`);
                if (salaryElement && stat.avg_salary_min && stat.avg_salary_max) {
                    salaryElement.textContent = `$${stat.avg_salary_min} - $${stat.avg_salary_max}/hr`;
                } else if (salaryElement) {
                    salaryElement.textContent = 'N/A';
                }

                // Update skills (only for Mercor)
                if (company === 'mercor') {
                    const skillsElement = document.getElementById(`${company}-skills`);
                    if (skillsElement) {
                        skillsElement.textContent = stat.unique_tags || 0;
                    }
                }
            }
        });
    }

    async loadMercorJobs() {
        const container = document.getElementById('mercor-jobs-container');
        container.innerHTML = '<div class="loading"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

        const tagFilter = document.getElementById('mercor-skill-filter').value;
        const searchQuery = document.getElementById('mercor-search').value;

        try {
            let url = `/api/mercor-jobs?page=${this.currentPage}&per_page=${this.perPage}`;
            if (tagFilter) url += `&tag=${tagFilter}`;

            const response = await fetch(url);
            const data = await response.json();

            this.renderMercorJobs(data.jobs);
            this.renderPagination(data);
        } catch (error) {
            console.error('Error loading Mercor jobs:', error);
            container.innerHTML = '<div class="alert alert-danger">Error loading jobs. Please try again.</div>';
        }
    }

    renderMercorJobs(jobs) {
        const container = document.getElementById('mercor-jobs-container');
        
        if (jobs.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No jobs found matching your criteria.</div>';
            return;
        }

        const searchQuery = document.getElementById('mercor-search').value.toLowerCase();
        
        const jobsHtml = jobs
            .filter(job => !searchQuery || job.title.toLowerCase().includes(searchQuery))
            .map(job => this.createJobCard(job))
            .join('');

        container.innerHTML = jobsHtml;
    }

    createJobCard(job) {
        const tagsHtml = job.tags.map(tag => `<span class="job-tag">${tag}</span>`).join('');
        
        return `
            <div class="col-lg-6 col-xl-4">
                <div class="job-card fade-in">
                    <div class="job-title">${this.escapeHtml(job.title)}</div>
                    <div class="job-location">
                        <i class="fas fa-map-marker-alt me-2"></i>${this.escapeHtml(job.location)}
                    </div>
                    ${job.compensation ? `<div class="job-compensation">${this.escapeHtml(job.compensation)}</div>` : ''}
                    <div class="job-description">${this.escapeHtml(job.description)}</div>
                    <div class="job-tags">${tagsHtml}</div>
                    <div class="job-actions">
                        <button class="btn btn-primary btn-sm" onclick="jobAnalysis.showSimilarJobs('${job.id}')">
                            <i class="fas fa-search me-1"></i>Find Similar
                        </button>
                        ${job.url ? `<a href="${job.url}" target="_blank" class="btn btn-outline-secondary btn-sm">
                            <i class="fas fa-external-link-alt me-1"></i>View Job
                        </a>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    renderPagination(data) {
        const pagination = document.getElementById('mercor-pagination');
        const totalPages = data.total_pages;
        const currentPage = data.page;

        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let paginationHtml = '';

        // Previous button
        paginationHtml += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="jobAnalysis.goToPage(${currentPage - 1})">Previous</a>
            </li>
        `;

        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="jobAnalysis.goToPage(${i})">${i}</a>
                </li>
            `;
        }

        // Next button
        paginationHtml += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="jobAnalysis.goToPage(${currentPage + 1})">Next</a>
            </li>
        `;

        pagination.innerHTML = paginationHtml;
    }

    goToPage(page) {
        this.currentPage = page;
        this.loadMercorJobs();
        window.scrollTo({ top: document.getElementById('mercor-jobs').offsetTop - 100, behavior: 'smooth' });
    }

    async showSimilarJobs(jobId) {
        const modal = new bootstrap.Modal(document.getElementById('similarJobsModal'));
        const container = document.getElementById('similar-jobs-container');
        
        container.innerHTML = '<div class="loading"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
        modal.show();

        try {
            const response = await fetch(`/api/similar-jobs/${jobId}`);
            const data = await response.json();

            // Update modal header
            document.getElementById('modal-mercor-job-title').textContent = data.mercor_job.title;
            document.getElementById('modal-mercor-job-skills').textContent = data.mercor_job.tags.join(', ');

            // Render similar jobs
            this.renderSimilarJobs(data.similar_jobs);
        } catch (error) {
            console.error('Error loading similar jobs:', error);
            container.innerHTML = '<div class="alert alert-danger">Error loading similar jobs. Please try again.</div>';
        }
    }

    renderSimilarJobs(jobs) {
        const container = document.getElementById('similar-jobs-container');
        
        if (jobs.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No similar jobs found from competitors.</div>';
            return;
        }

        const jobsHtml = jobs.map(job => `
            <div class="col-md-6">
                <div class="similar-job-card">
                    <div class="company-badge ${job.company}">${job.company}</div>
                    <span class="similarity-score">${(job.similarity * 100).toFixed(1)}% match</span>
                    <div class="job-title">${this.escapeHtml(job.title)}</div>
                    <div class="job-location">${this.escapeHtml(job.location)}</div>
                    ${job.compensation ? `<div class="job-compensation">${this.escapeHtml(job.compensation)}</div>` : ''}
                    <div class="job-description">${this.escapeHtml(job.description)}</div>
                    <div class="job-tags">${job.tags.map(tag => `<span class="job-tag">${tag}</span>`).join('')}</div>
                    ${job.url ? `<a href="${job.url}" target="_blank" class="btn btn-outline-primary btn-sm">
                        <i class="fas fa-external-link-alt me-1"></i>View Job
                    </a>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = jobsHtml;
    }

    initializeCharts() {
        this.createJobDistributionChart();
        this.createSalaryComparisonChart();
        this.createSkillsChart();
    }

    createJobDistributionChart() {
        const ctx = document.getElementById('job-distribution-chart');
        if (!ctx) return;

        const companies = ['mercor', 'afterquery', 'alignerr', 'handshake', 'outlier'];
        const data = companies.map(company => this.stats[company]?.total_jobs || 0);
        const labels = companies.map(company => company.charAt(0).toUpperCase() + company.slice(1));

        this.charts.jobDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#0d6efd', // mercor
                        '#198754', // afterquery
                        '#ffc107', // alignerr
                        '#dc3545', // handshake
                        '#6f42c1'  // outlier
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createSalaryComparisonChart() {
        const ctx = document.getElementById('salary-comparison-chart');
        if (!ctx) return;

        const companies = ['mercor', 'afterquery', 'alignerr', 'handshake', 'outlier'];
        const avgSalaries = companies.map(company => {
            const stat = this.stats[company];
            return stat?.avg_salary_min ? (stat.avg_salary_min + stat.avg_salary_max) / 2 : 0;
        });

        this.charts.salaryComparison = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: companies.map(company => company.charAt(0).toUpperCase() + company.slice(1)),
                datasets: [{
                    label: 'Average Hourly Rate ($)',
                    data: avgSalaries,
                    backgroundColor: [
                        '#0d6efd', // mercor
                        '#198754', // afterquery
                        '#ffc107', // alignerr
                        '#dc3545', // handshake
                        '#6f42c1'  // outlier
                    ],
                    borderWidth: 1,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Hourly Rate ($)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createSkillsChart() {
        const ctx = document.getElementById('skills-chart');
        if (!ctx) return;

        // This would need to be implemented with actual skills data
        // For now, showing a placeholder
        this.charts.skills = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Math & Stats', 'Computer Programming', 'Data Science', 'Finance', 'Biology'],
                datasets: [{
                    label: 'Job Count',
                    data: [150, 200, 180, 120, 90],
                    backgroundColor: '#0d6efd'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    updateSkillsChart() {
        // This would update the skills chart based on the selected filter
        // Implementation would depend on the actual data structure
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.jobAnalysis = new JobMarketAnalysis();
});

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add loading states to buttons
document.addEventListener('click', (e) => {
    if (e.target.matches('.btn')) {
        const originalText = e.target.innerHTML;
        e.target.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
        e.target.disabled = true;
        
        // Re-enable after a delay (for demo purposes)
        setTimeout(() => {
            e.target.innerHTML = originalText;
            e.target.disabled = false;
        }, 2000);
    }
}); 