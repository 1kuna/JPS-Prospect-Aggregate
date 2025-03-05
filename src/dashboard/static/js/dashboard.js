// Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const proposalsTableBody = document.getElementById('proposals-table-body');
    const proposalCount = document.getElementById('proposal-count');
    const loadingIndicator = document.getElementById('loading');
    const noResultsMessage = document.getElementById('no-results');
    const filterForm = document.getElementById('filter-form');
    const searchInput = document.getElementById('search');
    const sourceSelect = document.getElementById('source');
    const agencySelect = document.getElementById('agency');
    const statusSelect = document.getElementById('status');
    const naicsCodesSelect = document.getElementById('naics-codes');
    const sortBySelect = document.getElementById('sort-by');
    const sortOrderSelect = document.getElementById('sort-order');
    const resetFiltersButton = document.getElementById('reset-filters');
    const rebuildDbButton = document.getElementById('rebuild-db');
    const initDbButton = document.getElementById('init-db');
    const manageBackupsButton = document.getElementById('manage-backups');
    const resetEverythingButton = document.getElementById('reset-everything');
    const updateNotification = document.getElementById('update-notification');
    const refreshFromNotification = document.getElementById('refresh-from-notification');
    const proposalModal = new bootstrap.Modal(document.getElementById('proposal-modal'));
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const viewSourceButton = document.getElementById('view-source');
    
    // Backups elements
    const backupsModal = new bootstrap.Modal(document.getElementById('backupsModal'));
    const backupsTableBody = document.getElementById('backups-table-body');
    const maxBackupsInput = document.getElementById('max-backups');
    const cleanupBackupsButton = document.getElementById('cleanup-backups');
    
    // Statistics elements
    const statsModal = document.getElementById('stats-modal');
    const statsLoading = document.getElementById('stats-loading');
    const statsContent = document.getElementById('stats-content');
    const totalProposals = document.getElementById('total-proposals');
    const sourceStats = document.getElementById('source-stats');
    const agencyStats = document.getElementById('agency-stats');
    const statusStats = document.getElementById('status-stats');
    
    // Current filters and sort options
    let currentFilters = {
        search: '',
        source_id: '',
        agency: '',
        status: '',
        naics_codes: [],
        sort_by: 'release_date',
        sort_order: 'desc'
    };
    
    // Track the last time we checked for updates
    let lastUpdateCheck = null;
    
    // Update check interval (in milliseconds) - check every 10 seconds for updates
    const updateCheckInterval = 10 * 1000;
    
    // Initialize the dashboard
    initializeDashboard();
    
    // Start periodic update checks
    startUpdateChecks();
    
    // Event listeners
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
    });
    
    resetFiltersButton.addEventListener('click', function(e) {
        e.preventDefault();
        resetFilters();
    });
    
    sortBySelect.addEventListener('change', function() {
        currentFilters.sort_by = this.value;
        loadProposals();
    });
    
    sortOrderSelect.addEventListener('change', function() {
        currentFilters.sort_order = this.value;
        loadProposals();
    });
    
    refreshFromNotification.addEventListener('click', function(e) {
        e.preventDefault();
        // Hide the notification
        updateNotification.classList.add('d-none');
        // Refresh the data
        loadProposals();
        // Update the last check time
        lastUpdateCheck = new Date().toISOString();
    });
    
    rebuildDbButton.addEventListener('click', function(e) {
        e.preventDefault();
        rebuildDatabase();
    });
    
    initDbButton.addEventListener('click', function(e) {
        e.preventDefault();
        initializeDatabase();
    });
    
    manageBackupsButton.addEventListener('click', function(e) {
        e.preventDefault();
        openBackupsModal();
    });
    
    resetEverythingButton.addEventListener('click', function(e) {
        e.preventDefault();
        resetEverything();
    });
    
    // Add event listener for statistics modal
    statsModal.addEventListener('show.bs.modal', function() {
        loadStatistics();
    });
    
    // Functions
    function initializeDashboard() {
        // Load filter options
        loadFilterOptions();
        
        // Load initial proposals
        loadProposals();
    }
    
    function loadFilterOptions() {
        // Load data sources
        fetch('/api/sources')
            .then(response => response.json())
            .then(sources => {
                sourceSelect.innerHTML = '<option value="">All Sources</option>';
                sources.forEach(source => {
                    const option = document.createElement('option');
                    option.value = source.id;
                    option.textContent = source.name;
                    sourceSelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading sources:', error));
        
        // Load filter options (agencies, statuses, naics codes)
        fetch('/api/filters')
            .then(response => response.json())
            .then(filters => {
                // Populate agencies
                agencySelect.innerHTML = '<option value="">All Agencies</option>';
                filters.agencies.forEach(agency => {
                    const option = document.createElement('option');
                    option.value = agency;
                    option.textContent = agency;
                    agencySelect.appendChild(option);
                });
                
                // Populate statuses
                statusSelect.innerHTML = '<option value="">All Statuses</option>';
                filters.statuses.forEach(status => {
                    const option = document.createElement('option');
                    option.value = status;
                    option.textContent = status;
                    statusSelect.appendChild(option);
                });
                
                // Populate NAICS codes
                naicsCodesSelect.innerHTML = '';
                if (filters.naics_codes && filters.naics_codes.length > 0) {
                    // Sort NAICS codes numerically
                    filters.naics_codes.sort((a, b) => {
                        return a.localeCompare(b, undefined, {numeric: true});
                    });
                    
                    filters.naics_codes.forEach(naicsCode => {
                        const option = document.createElement('option');
                        option.value = naicsCode;
                        option.textContent = naicsCode;
                        naicsCodesSelect.appendChild(option);
                    });
                }
            })
            .catch(error => console.error('Error loading filter options:', error));
    }
    
    function applyFilters() {
        currentFilters.search = searchInput.value;
        currentFilters.source_id = sourceSelect.value;
        currentFilters.agency = agencySelect.value;
        currentFilters.status = statusSelect.value;
        
        // Get selected NAICS codes
        currentFilters.naics_codes = Array.from(naicsCodesSelect.selectedOptions).map(option => option.value);
        
        loadProposals();
    }
    
    function resetFilters() {
        searchInput.value = '';
        sourceSelect.value = '';
        agencySelect.value = '';
        statusSelect.value = '';
        
        // Clear NAICS code selections
        for (let i = 0; i < naicsCodesSelect.options.length; i++) {
            naicsCodesSelect.options[i].selected = false;
        }
        
        sortBySelect.value = 'release_date';
        sortOrderSelect.value = 'desc';
        
        currentFilters = {
            search: '',
            source_id: '',
            agency: '',
            status: '',
            naics_codes: [],
            sort_by: 'release_date',
            sort_order: 'desc'
        };
        
        loadProposals();
    }
    
    function loadProposals() {
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        noResultsMessage.classList.add('d-none');
        proposalsTableBody.innerHTML = '';
        
        // Build query string
        const queryParams = new URLSearchParams();
        if (currentFilters.search) queryParams.append('search', currentFilters.search);
        if (currentFilters.source_id) queryParams.append('source_id', currentFilters.source_id);
        if (currentFilters.agency) queryParams.append('agency', currentFilters.agency);
        if (currentFilters.status) queryParams.append('status', currentFilters.status);
        
        // Add NAICS codes to query params
        if (currentFilters.naics_codes && currentFilters.naics_codes.length > 0) {
            currentFilters.naics_codes.forEach(code => {
                queryParams.append('naics_codes[]', code);
            });
        }
        
        // Check if any filters are applied
        const hasFilters = currentFilters.search || currentFilters.source_id || 
                          currentFilters.agency || currentFilters.status || 
                          (currentFilters.naics_codes && currentFilters.naics_codes.length > 0);
        
        // If no filters are applied, show all proposals to match statistics
        if (!hasFilters) {
            queryParams.append('only_latest', 'false');
        } else {
            // Otherwise use the default (only latest)
            queryParams.append('only_latest', 'true');
        }
        
        queryParams.append('sort_by', currentFilters.sort_by);
        queryParams.append('sort_order', currentFilters.sort_order);
        
        // Fetch proposals
        fetch(`/api/proposals?${queryParams.toString()}`)
            .then(response => response.json())
            .then(data => {
                // Hide loading indicator
                loadingIndicator.classList.add('d-none');
                
                // Check if the response has the expected structure
                if (data.status === 'error') {
                    // Show error message
                    noResultsMessage.classList.remove('d-none');
                    noResultsMessage.textContent = data.message || 'Error loading proposals. Please try again.';
                    return;
                }
                
                // Get the proposals array from the data property
                const proposals = data.data || [];
                
                // Update proposal count
                proposalCount.textContent = `${proposals.length} proposals`;
                
                if (proposals.length === 0) {
                    // Show no results message
                    noResultsMessage.classList.remove('d-none');
                } else {
                    // Populate table
                    proposals.forEach(proposal => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${proposal.title}</td>
                            <td>${proposal.agency || 'N/A'}</td>
                            <td>${formatDate(proposal.release_date)}</td>
                            <td>${formatDate(proposal.response_date)}</td>
                            <td class="currency">${formatCurrency(proposal.estimated_value)}</td>
                            <td><span class="badge bg-secondary badge-status">${proposal.status || 'Unknown'}</span></td>
                            <td>
                                <button class="btn btn-sm btn-primary view-details" data-proposal-id="${proposal.id}">
                                    <i class="bi bi-info-circle"></i> Details
                                </button>
                            </td>
                        `;
                        
                        // Add click event to view details
                        row.querySelector('.view-details').addEventListener('click', function() {
                            showProposalDetails(proposal);
                        });
                        
                        proposalsTableBody.appendChild(row);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading proposals:', error);
                loadingIndicator.classList.add('d-none');
                noResultsMessage.classList.remove('d-none');
                noResultsMessage.textContent = 'Error loading proposals. Please try again.';
            });
    }
    
    function showProposalDetails(proposal) {
        // Set modal title
        modalTitle.textContent = proposal.title;
        
        // Set view source button URL
        if (proposal.url) {
            viewSourceButton.href = proposal.url;
            viewSourceButton.classList.remove('d-none');
        } else {
            viewSourceButton.classList.add('d-none');
        }
        
        // Build modal body content
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Agency</p>
                    <p class="proposal-detail-value">${proposal.agency || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Office</p>
                    <p class="proposal-detail-value">${proposal.office || 'N/A'}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Release Date</p>
                    <p class="proposal-detail-value">${formatDate(proposal.release_date)}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Response Date</p>
                    <p class="proposal-detail-value">${formatDate(proposal.response_date)}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Estimated Value</p>
                    <p class="proposal-detail-value">${formatCurrency(proposal.estimated_value)}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">NAICS Code</p>
                    <p class="proposal-detail-value">${proposal.naics_code || 'N/A'}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Status</p>
                    <p class="proposal-detail-value">
                        <span class="badge bg-secondary badge-status">${proposal.status || 'Unknown'}</span>
                    </p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Last Updated</p>
                    <p class="proposal-detail-value">${formatDate(proposal.last_updated)}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Contract Type</p>
                    <p class="proposal-detail-value">${proposal.contract_type || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Set Aside</p>
                    <p class="proposal-detail-value">${proposal.set_aside || 'N/A'}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Competition Type</p>
                    <p class="proposal-detail-value">${proposal.competition_type || 'N/A'}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Solicitation Number</p>
                    <p class="proposal-detail-value">${proposal.solicitation_number || 'N/A'}</p>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <p class="proposal-detail-label">Award Date</p>
                    <p class="proposal-detail-value">${formatDate(proposal.award_date)}</p>
                </div>
                <div class="col-md-6">
                    <p class="proposal-detail-label">Incumbent</p>
                    <p class="proposal-detail-value">${proposal.incumbent || 'N/A'}</p>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <p class="proposal-detail-label">Description</p>
                    <p class="proposal-detail-value">${proposal.description || 'No description available.'}</p>
                </div>
            </div>
            
            <div class="row mt-3">
                <div class="col-12">
                    <p class="proposal-detail-label">Contact Information</p>
                    <p class="proposal-detail-value">${proposal.contact_info || 'No contact information available.'}</p>
                </div>
            </div>
        `;
        
        // Show the modal
        proposalModal.show();
    }
    
    function rebuildDatabase() {
        // Confirm with the user
        if (!confirm('Are you sure you want to rebuild the database? This will delete all existing data and recreate the database structure.')) {
            return;
        }
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.classList.remove('d-none');
        }
        
        // Call the API to rebuild the database
        fetch('/data-sources/rebuild-db', {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || err.message || `HTTP error! Status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
            }
            
            if (data.status === 'success') {
                // Show success message in the notification area
                const notificationArea = document.getElementById('notification-area') || document.createElement('div');
                if (!document.getElementById('notification-area')) {
                    notificationArea.id = 'notification-area';
                    notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                    document.body.appendChild(notificationArea);
                }
                
                const toastId = 'rebuild-toast-' + Date.now();
                notificationArea.innerHTML += `
                    <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header bg-success text-white">
                            <strong class="me-auto">Database Rebuild</strong>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                        </div>
                        <div class="toast-body">
                            Database rebuild initiated. The application may need to be restarted to use the new database.
                        </div>
                    </div>
                `;
                
                // Auto-remove toast after 5 seconds
                setTimeout(() => {
                    const toast = document.getElementById(toastId);
                    if (toast) toast.remove();
                }, 5000);
            } else {
                // Show error message in the notification area
                const notificationArea = document.getElementById('notification-area') || document.createElement('div');
                if (!document.getElementById('notification-area')) {
                    notificationArea.id = 'notification-area';
                    notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                    document.body.appendChild(notificationArea);
                }
                
                const toastId = 'error-toast-' + Date.now();
                notificationArea.innerHTML += `
                    <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header bg-danger text-white">
                            <strong class="me-auto">Error</strong>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                        </div>
                        <div class="toast-body">
                            Error rebuilding database: ${data.message || 'Unknown error'}
                        </div>
                    </div>
                `;
                
                // Auto-remove toast after 5 seconds
                setTimeout(() => {
                    const toast = document.getElementById(toastId);
                    if (toast) toast.remove();
                }, 5000);
            }
        })
        .catch(error => {
            console.error('Error rebuilding database:', error);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
            }
            
            // Show error message in the notification area
            const notificationArea = document.getElementById('notification-area') || document.createElement('div');
            if (!document.getElementById('notification-area')) {
                notificationArea.id = 'notification-area';
                notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(notificationArea);
            }
            
            const toastId = 'error-toast-' + Date.now();
            notificationArea.innerHTML += `
                <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header bg-danger text-white">
                        <strong class="me-auto">Error</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                    </div>
                    <div class="toast-body">
                        ${error.message || 'Error rebuilding database. Please check the console for details.'}
                    </div>
                </div>
            `;
            
            // Auto-remove toast after 5 seconds
            setTimeout(() => {
                const toast = document.getElementById(toastId);
                if (toast) toast.remove();
            }, 5000);
        });
    }
    
    function initializeDatabase() {
        // Confirm with the user
        if (!confirm('Are you sure you want to initialize the database? This will create the database structure if it does not exist.')) {
            return;
        }
        
        // Show loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.classList.remove('d-none');
        }
        
        // Call the API to initialize the database
        fetch('/api/init-db', {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || err.message || `HTTP error! Status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
            }
            
            if (data.status === 'success') {
                // Show success message in the notification area
                const notificationArea = document.getElementById('notification-area') || document.createElement('div');
                if (!document.getElementById('notification-area')) {
                    notificationArea.id = 'notification-area';
                    notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                    document.body.appendChild(notificationArea);
                }
                
                const toastId = 'init-toast-' + Date.now();
                notificationArea.innerHTML += `
                    <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header bg-success text-white">
                            <strong class="me-auto">Database Initialized</strong>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                        </div>
                        <div class="toast-body">
                            Database initialized successfully!
                        </div>
                    </div>
                `;
                
                // Auto-remove toast after 5 seconds
                setTimeout(() => {
                    const toast = document.getElementById(toastId);
                    if (toast) toast.remove();
                }, 5000);
            } else {
                // Show error message in the notification area
                const notificationArea = document.getElementById('notification-area') || document.createElement('div');
                if (!document.getElementById('notification-area')) {
                    notificationArea.id = 'notification-area';
                    notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                    document.body.appendChild(notificationArea);
                }
                
                const toastId = 'error-toast-' + Date.now();
                notificationArea.innerHTML += `
                    <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header bg-danger text-white">
                            <strong class="me-auto">Error</strong>
                            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                        </div>
                        <div class="toast-body">
                            Error initializing database: ${data.message || 'Unknown error'}
                        </div>
                    </div>
                `;
                
                // Auto-remove toast after 5 seconds
                setTimeout(() => {
                    const toast = document.getElementById(toastId);
                    if (toast) toast.remove();
                }, 5000);
            }
        })
        .catch(error => {
            console.error('Error initializing database:', error);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.classList.add('d-none');
            }
            
            // Show error message in the notification area
            const notificationArea = document.getElementById('notification-area') || document.createElement('div');
            if (!document.getElementById('notification-area')) {
                notificationArea.id = 'notification-area';
                notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(notificationArea);
            }
            
            const toastId = 'error-toast-' + Date.now();
            notificationArea.innerHTML += `
                <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header bg-danger text-white">
                        <strong class="me-auto">Error</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                    </div>
                    <div class="toast-body">
                        ${error.message || 'Error initializing database. Please check the console for details.'}
                    </div>
                </div>
            `;
            
            // Auto-remove toast after 5 seconds
            setTimeout(() => {
                const toast = document.getElementById(toastId);
                if (toast) toast.remove();
            }, 5000);
        });
    }
    
    function loadStatistics() {
        // Show loading indicator
        statsLoading.classList.remove('d-none');
        statsContent.classList.add('d-none');
        
        // Check if any filters are applied
        const hasFilters = currentFilters.search || currentFilters.source_id || 
                          currentFilters.agency || currentFilters.status || 
                          (currentFilters.naics_codes && currentFilters.naics_codes.length > 0);
        
        // Set only_latest parameter to match the current dashboard view
        const onlyLatest = hasFilters ? 'true' : 'false';
        
        // Fetch statistics
        fetch(`/api/statistics?only_latest=${onlyLatest}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Update the statistics
                totalProposals.textContent = data.total_proposals;
                
                // Update source stats
                sourceStats.innerHTML = '';
                Object.entries(data.by_source).forEach(([name, count]) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td>${count}</td>
                    `;
                    sourceStats.appendChild(row);
                });
                
                // Update agency stats
                agencyStats.innerHTML = '';
                Object.entries(data.by_agency).forEach(([agency, count]) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${agency}</td>
                        <td>${count}</td>
                    `;
                    agencyStats.appendChild(row);
                });
                
                // Update status stats
                statusStats.innerHTML = '';
                Object.entries(data.by_status).forEach(([status, count]) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${status}</td>
                        <td>${count}</td>
                    `;
                    statusStats.appendChild(row);
                });
                
                // Add a note about what data is being shown
                const noteElement = document.createElement('div');
                noteElement.className = 'alert alert-info mt-3';
                noteElement.innerHTML = data.only_latest 
                    ? 'Note: Statistics are showing only the latest version of each proposal.'
                    : 'Note: Statistics are showing all proposals, including historical versions.';
                statsContent.appendChild(noteElement);
                
                // Hide loading indicator and show content
                statsLoading.classList.add('d-none');
                statsContent.classList.remove('d-none');
            })
            .catch(error => {
                console.error('Error loading statistics:', error);
                statsLoading.classList.add('d-none');
                
                // Display error in the UI instead of an alert
                statsContent.innerHTML = `
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">Error Loading Statistics</h4>
                        <p>${error.message || 'An unexpected error occurred. Please try again later.'}</p>
                        <hr>
                        <p class="mb-0">
                            <button class="btn btn-outline-danger btn-sm" onclick="loadStatistics()">
                                <i class="bi bi-arrow-clockwise"></i> Try Again
                            </button>
                        </p>
                    </div>
                `;
                statsContent.classList.remove('d-none');
            });
    }
    
    function startUpdateChecks() {
        // Get the initial server timestamp before starting checks
        fetch('/api/check-updates')
            .then(response => response.json())
            .then(data => {
                // Initialize with the server's timestamp to avoid false positives
                if (data.last_refresh) {
                    lastUpdateCheck = data.last_refresh;
                    console.log(`Initialized update check with server timestamp: ${lastUpdateCheck}`);
                } else {
                    // If no server timestamp, use current time
                    lastUpdateCheck = new Date().toISOString();
                    console.log(`No server timestamp available, using current time: ${lastUpdateCheck}`);
                }
                
                // Set up periodic checks after initializing
                setInterval(checkForUpdates, updateCheckInterval);
            })
            .catch(error => {
                console.error('Error initializing update checks:', error);
                // Still set up checks even if initialization fails
                lastUpdateCheck = new Date().toISOString();
                setInterval(checkForUpdates, updateCheckInterval);
            });
    }
    
    function checkForUpdates() {
        // Skip check if lastUpdateCheck is not initialized
        if (!lastUpdateCheck) {
            console.log('Skipping update check - not initialized yet');
            return;
        }
        
        // Log update check (only visible in browser console)
        console.log(`Checking for updates at ${new Date().toLocaleTimeString()}...`);
        
        // Make a request to check for updates
        fetch(`/api/check-updates?last_check=${encodeURIComponent(lastUpdateCheck)}`, {
            // Use cache: 'no-store' to ensure we always get fresh data
            cache: 'no-store',
            // Add a timestamp to prevent caching
            headers: {
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.updates_available) {
                    // Show the notification
                    updateNotification.classList.remove('d-none');
                    console.log('New updates available!');
                    
                    // Update the last refresh time if available
                    if (data.last_refresh) {
                        lastUpdateCheck = data.last_refresh;
                    }
                } else {
                    console.log('No new updates available');
                    
                    // Still update the timestamp to stay in sync with server
                    if (data.last_refresh) {
                        lastUpdateCheck = data.last_refresh;
                    }
                }
            })
            .catch(error => {
                console.error('Error checking for updates:', error);
            });
    }
    
    // Helper functions
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
    
    function formatCurrency(value) {
        if (value === null || value === undefined) return 'N/A';
        
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }
    
    // Function to open the backups modal and load the backups
    function openBackupsModal() {
        // Show the modal
        backupsModal.show();
        
        // Load the backups
        loadBackups();
    }
    
    // Function to load the database backups
    function loadBackups() {
        // Show loading message
        backupsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">Loading backups...</td></tr>';
        
        // Fetch the backups from the API
        fetch('/api/database-backups')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Clear the table
                    backupsTableBody.innerHTML = '';
                    
                    // Check if there are any backups
                    if (data.backups.length === 0) {
                        backupsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">No backups found</td></tr>';
                        return;
                    }
                    
                    // Add each backup to the table
                    data.backups.forEach(backup => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${backup.file}</td>
                            <td>${backup.size}</td>
                            <td>${backup.created}</td>
                        `;
                        backupsTableBody.appendChild(row);
                    });
                } else {
                    // Show error message
                    backupsTableBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">Error: ${data.message}</td></tr>`;
                }
            })
            .catch(error => {
                console.error('Error loading backups:', error);
                backupsTableBody.innerHTML = '<tr><td colspan="3" class="text-center text-danger">Error loading backups. Please try again.</td></tr>';
            });
    }
    
    // Function to clean up old backups
    function cleanupBackups() {
        // Get the maximum number of backups to keep
        const maxBackups = parseInt(maxBackupsInput.value);
        
        // Validate the input
        if (isNaN(maxBackups) || maxBackups < 1) {
            alert('Please enter a valid number of backups to keep (minimum 1)');
            return;
        }
        
        // Confirm the action
        if (!confirm(`This will permanently delete all but the ${maxBackups} most recent backups. Are you sure you want to continue?`)) {
            return;
        }
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        
        // Call the API to clean up old backups
        fetch('/api/database-backups/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                max_backups: maxBackups
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            
            if (data.status === 'success') {
                // Show success message
                alert(data.message);
                
                // Update the backups table
                backupsTableBody.innerHTML = '';
                
                // Check if there are any backups
                if (data.backups.length === 0) {
                    backupsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">No backups found</td></tr>';
                    return;
                }
                
                // Add each backup to the table
                data.backups.forEach(backup => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${backup.file}</td>
                        <td>${backup.size}</td>
                        <td>${backup.created}</td>
                    `;
                    backupsTableBody.appendChild(row);
                });
            } else {
                // Show error message
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error cleaning up backups:', error);
            loadingIndicator.classList.add('d-none');
            alert('Error cleaning up backups. Please try again.');
        });
    }
    
    // Add event listener for the cleanup backups button
    cleanupBackupsButton.addEventListener('click', function() {
        cleanupBackups();
    });
    
    // Function to reset everything (downloads and database)
    function resetEverything() {
        // Create a detailed confirmation dialog
        const confirmMessage = 
            'WARNING: This is a destructive operation!\n\n' +
            'This will:\n' +
            '1. Delete ALL downloaded files\n' +
            '2. Delete ALL database backups\n' +
            '3. Delete the current database\n' +
            '4. Create a new empty database\n\n' +
            'This operation cannot be undone. All your data will be permanently lost.\n\n' +
            'Are you absolutely sure you want to proceed?';
            
        if (confirm(confirmMessage)) {
            // Double-check with a second confirmation
            if (confirm('FINAL WARNING: You are about to delete ALL data. This cannot be undone. Type "RESET" to confirm.')) {
                const userInput = prompt('Type "RESET" to confirm:');
                if (userInput === 'RESET') {
                    // Show loading indicator
                    loadingIndicator.classList.remove('d-none');
                    
                    // Call the API to reset everything
                    fetch('/api/reset-everything', {
                        method: 'POST'
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Hide loading indicator
                        loadingIndicator.classList.add('d-none');
                        
                        if (data.status === 'success') {
                            alert('Reset initiated. The application will be reloaded when the reset is complete.');
                            
                            // Reload the page after a short delay
                            setTimeout(() => {
                                window.location.reload();
                            }, 5000);
                        } else {
                            alert('Error resetting: ' + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error resetting:', error);
                        loadingIndicator.classList.add('d-none');
                        alert('Error resetting. Please check the console for details.');
                    });
                } else {
                    alert('Reset cancelled. You did not type "RESET" correctly.');
                }
            }
        }
    }
}); 