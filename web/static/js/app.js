// Life DB Frontend Application

class LifeDB {
    constructor() {
        this.currentQuery = '';
        this.currentFilters = {
            file_type: null,
            author: null
        };
        this.searchTimeout = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadStats();
        this.loadFacets();
        this.showWelcome();
    }

    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.performSearch(e.target.value);
                }, 300);
            });

            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    clearTimeout(this.searchTimeout);
                    this.performSearch(e.target.value);
                }
            });
        }

        // Filter selects
        const fileTypeFilter = document.getElementById('file-type-filter');
        if (fileTypeFilter) {
            fileTypeFilter.addEventListener('change', (e) => {
                this.currentFilters.file_type = e.target.value || null;
                this.performSearch(this.currentQuery);
            });
        }

        const authorFilter = document.getElementById('author-filter');
        if (authorFilter) {
            authorFilter.addEventListener('change', (e) => {
                this.currentFilters.author = e.target.value || null;
                this.performSearch(this.currentQuery);
            });
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();

            document.getElementById('total-docs').textContent = stats.total_documents.toLocaleString();
            document.getElementById('file-types').textContent = stats.file_types.length;
            document.getElementById('total-size').textContent = stats.total_size_mb.toFixed(1) + ' MB';
            document.getElementById('recent-docs').textContent = stats.indexed_last_week;

        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    async loadFacets() {
        try {
            const response = await fetch('/api/facets');
            const facets = await response.json();

            // Populate file type filter
            const fileTypeFilter = document.getElementById('file-type-filter');
            if (fileTypeFilter && facets.file_types) {
                facets.file_types.forEach(ft => {
                    const option = document.createElement('option');
                    option.value = ft.value;
                    option.textContent = `${ft.value} (${ft.count})`;
                    fileTypeFilter.appendChild(option);
                });
            }

            // Populate author filter
            const authorFilter = document.getElementById('author-filter');
            if (authorFilter && facets.authors) {
                facets.authors.forEach(author => {
                    const option = document.createElement('option');
                    option.value = author.value;
                    option.textContent = `${author.value} (${author.count})`;
                    authorFilter.appendChild(option);
                });
            }

        } catch (error) {
            console.error('Error loading facets:', error);
        }
    }

    async performSearch(query) {
        this.currentQuery = query;

        const resultsDiv = document.getElementById('results');
        const searchMeta = document.getElementById('search-meta');

        if (!query || query.length < 2) {
            this.showWelcome();
            return;
        }

        // Show loading
        this.showLoading();

        try {
            const requestBody = {
                query: query,
                limit: 50,
                offset: 0,
                ...this.currentFilters
            };

            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error('Search failed');
            }

            const data = await response.json();

            // Update meta information
            if (searchMeta) {
                searchMeta.textContent = `Found ${data.total} results in ${data.took_ms}ms`;
            }

            // Display results
            this.displayResults(data.results);

        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        }
    }

    displayResults(results) {
        const resultsDiv = document.getElementById('results');

        if (results.length === 0) {
            this.showEmpty();
            return;
        }

        const html = results.map(result => this.createResultHTML(result)).join('');
        resultsDiv.innerHTML = html;

        // Add click handlers
        resultsDiv.querySelectorAll('.result-item').forEach((item, index) => {
            item.addEventListener('click', () => {
                this.showDocument(results[index]);
            });
        });
    }

    createResultHTML(result) {
        const icon = this.getFileIcon(result.file_type);
        const badge = this.getFileBadge(result.file_type);
        const date = result.modified_date ? new Date(result.modified_date).toLocaleDateString() : 'Unknown';

        return `
            <div class="result-item" data-id="${result.id}">
                <div class="result-header">
                    <div class="file-icon">${icon}</div>
                    <div class="result-title">
                        <div class="result-filename">${this.escapeHtml(result.title || result.filename)}</div>
                        <div class="result-path">${this.escapeHtml(result.filepath)}</div>
                    </div>
                </div>
                <div class="result-snippet">${result.snippet}</div>
                <div class="result-meta">
                    <span class="badge ${badge.class}">${badge.text}</span>
                    <span class="meta-item">📅 ${date}</span>
                    ${result.author ? `<span class="meta-item">👤 ${this.escapeHtml(result.author)}</span>` : ''}
                </div>
            </div>
        `;
    }

    getFileIcon(fileType) {
        const icons = {
            '.pdf': '📄',
            '.docx': '📝',
            '.doc': '📝',
            '.xlsx': '📊',
            '.xls': '📊',
            '.pptx': '📽️',
            '.ppt': '📽️',
            '.msg': '📧',
            '.eml': '📧',
            '.png': '🖼️',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.txt': '📃',
            '.md': '📃'
        };
        return icons[fileType] || '📁';
    }

    getFileBadge(fileType) {
        const badges = {
            '.pdf': { text: 'PDF', class: 'badge-pdf' },
            '.docx': { text: 'Word', class: 'badge-docx' },
            '.doc': { text: 'Word', class: 'badge-docx' },
            '.xlsx': { text: 'Excel', class: 'badge-xlsx' },
            '.xls': { text: 'Excel', class: 'badge-xlsx' },
            '.pptx': { text: 'PowerPoint', class: 'badge-pptx' },
            '.ppt': { text: 'PowerPoint', class: 'badge-pptx' },
            '.msg': { text: 'Email', class: 'badge-email' },
            '.eml': { text: 'Email', class: 'badge-email' },
            '.png': { text: 'Image', class: 'badge-image' },
            '.jpg': { text: 'Image', class: 'badge-image' },
            '.jpeg': { text: 'Image', class: 'badge-image' }
        };
        return badges[fileType] || { text: fileType.substring(1).toUpperCase(), class: 'badge-default' };
    }

    async showDocument(result) {
        try {
            const response = await fetch(`/api/documents/${result.id}`);
            const doc = await response.json();

            // Create modal or detail view
            // For now, just log to console
            console.log('Document:', doc);

            // You could implement a modal here to show full content
            alert(`Document: ${doc.title || doc.filename}\n\nClick OK to download the original file.`);

            // Download original file
            window.open(`/api/documents/${result.id}/download`, '_blank');

        } catch (error) {
            console.error('Error loading document:', error);
            alert('Failed to load document');
        }
    }

    showWelcome() {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <div class="empty-title">Search Your Documents</div>
                <div class="empty-description">
                    Enter a search query to find documents across all your files
                </div>
            </div>
        `;
    }

    showLoading() {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <div>Searching...</div>
            </div>
        `;
    }

    showEmpty() {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">😕</div>
                <div class="empty-title">No Results Found</div>
                <div class="empty-description">
                    Try a different search query or adjust your filters
                </div>
            </div>
        `;
    }

    showError(message) {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Error</div>
                <div class="empty-description">${this.escapeHtml(message)}</div>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.lifeDB = new LifeDB();
});
