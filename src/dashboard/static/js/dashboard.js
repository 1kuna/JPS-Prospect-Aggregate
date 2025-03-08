// Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const proposalsTableBody = document.getElementById('proposals-table-body');
    const proposalCount = document.getElementById('proposal-count');
    const loadingIndicator = document.getElementById('loading');
    const noResultsMessage = document.getElementById('no-results');
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
    const paginationElement = document.getElementById('pagination');
    const pageInfoElement = document.getElementById('page-info');
    const perPageSelect = document.getElementById('per-page-select');
    
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
    
    // Pagination state
    let currentState = {
        page: 1,
        per_page: 20
    };
    
    // Initialize
    loadProposals();
    
    // Event listeners
    if (perPageSelect) {
        // Set the initial value in the dropdown to match the currentState
        if (perPageSelect.querySelector(`option[value="${currentState.per_page}"]`)) {
            perPageSelect.value = currentState.per_page.toString();
        }
        
        perPageSelect.addEventListener('change', function() {
            const oldPerPage = currentState.per_page;
            const newPerPage = parseInt(this.value);
            
            console.log('perPageSelect changed:', { 
                oldValue: oldPerPage, 
                newValue: newPerPage,
                selectValue: this.value
            });
            
            currentState.per_page = newPerPage;
            currentState.page = 1; // Reset to first page
            
            console.log('Updated currentState:', { ...currentState });
            
            loadProposals();
        });
    }
    
    if (refreshFromNotification) {
        refreshFromNotification.addEventListener('click', function(e) {
            e.preventDefault();
            loadProposals();
            if (updateNotification) {
                updateNotification.classList.add('d-none');
            }
        });
    }
    
    // Load proposals with pagination
    function loadProposals() {
        if (loadingIndicator) {
            loadingIndicator.classList.remove('d-none');
        }
        if (proposalsTableBody) {
            proposalsTableBody.innerHTML = '';
        }
        if (noResultsMessage) {
            noResultsMessage.classList.add('d-none');
        }
        
        // Log current pagination state
        console.log('Loading proposals with pagination:', currentState);
        
        // Build URL with pagination parameters
        const url = `/api/proposals?page=${currentState.page}&per_page=${currentState.per_page}`;
        console.log('Fetching proposals from URL:', url);
        console.log('URL parameters:', {
            page: currentState.page,
            per_page: currentState.per_page,
            'page type': typeof currentState.page,
            'per_page type': typeof currentState.per_page
        });
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.message || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('API response:', data);
                console.log('Requested per_page:', currentState.per_page);
                console.log('Actual data length:', data.data ? data.data.length : 0);
                console.log('Pagination info in response:', data.pagination);
                
                // DEBUG: Print the first few IDs to verify data
                if (data.data && data.data.length > 0) {
                    const sampleIds = data.data.slice(0, Math.min(5, data.data.length)).map(p => p.id);
                    console.log('Sample proposal IDs:', sampleIds);
                }
                
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                
                if (data.status === 'success' && data.data.length > 0) {
                    console.log('About to render', data.data.length, 'proposals');
                    renderProposals(data.data);
                    if (data.pagination) {
                        console.log('Pagination data received:', data.pagination);
                        console.log('Total count:', data.pagination.total_count, 'Total pages:', data.pagination.total_pages);
                        renderPagination(data.pagination);
                    } else {
                        console.warn('No pagination data received in the API response');
                    }
                    if (proposalCount) {
                        proposalCount.textContent = data.pagination ? data.pagination.total_count : data.data.length;
                    }
                } else {
                    if (noResultsMessage) {
                        noResultsMessage.classList.remove('d-none');
                    }
                    if (proposalCount) {
                        proposalCount.textContent = '0';
                    }
                    if (paginationElement) {
                        paginationElement.innerHTML = '';
                    }
                    if (pageInfoElement) {
                        pageInfoElement.textContent = '';
                    }
                }
            })
            .catch(error => {
                console.error('Error loading proposals:', error);
                if (loadingIndicator) {
                    loadingIndicator.classList.add('d-none');
                }
                if (noResultsMessage) {
                    noResultsMessage.textContent = `Error: ${error.message}`;
                    noResultsMessage.classList.remove('d-none');
                }
            });
    }
    
    // Render proposals to the table
    function renderProposals(proposals) {
        if (!proposalsTableBody) return;
        
        console.log('Inside renderProposals with', proposals.length, 'proposals');
        
        proposalsTableBody.innerHTML = '';
        
        // DEBUG: Track how many items we actually process
        let renderedCount = 0;
        
        proposals.forEach(proposal => {
            renderedCount++;
            const row = document.createElement('tr');
            row.className = 'proposal-row';
            row.setAttribute('data-id', proposal.id);
            
            // Format the date
            const releaseDate = proposal.release_date ? new Date(proposal.release_date).toLocaleDateString() : 'N/A';
            
            // Create the row content
            row.innerHTML = `
                <td>${proposal.id}</td>
                <td>${proposal.title}</td>
                <td>${proposal.source_name || 'N/A'}</td>
                <td>${releaseDate}</td>
                <td><span class="badge bg-${getStatusColor(proposal.status)}">${proposal.status || 'N/A'}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary view-details" data-id="${proposal.id}">
                        <i class="bi bi-eye"></i> View
                    </button>
                </td>
            `;
            
            // Add event listener to the view button
            const viewButton = row.querySelector('.view-details');
            if (viewButton) {
                viewButton.addEventListener('click', function() {
                    showProposalDetails(proposal);
                });
            }
            
            proposalsTableBody.appendChild(row);
        });
        
        console.log('Finished rendering', renderedCount, 'proposals');
    }
    
    // Function to load statistics
    function loadStatistics() {
        // Show loading indicator
        statsLoading.classList.remove('d-none');
        statsContent.classList.add('d-none');
        
        // Fetch statistics
        fetch(`/api/statistics`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || `HTTP error! Status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                statsLoading.classList.add('d-none');
                statsContent.classList.remove('d-none');
                
                // Update statistics
                if (totalProposals) {
                    totalProposals.textContent = data.data.total_proposals;
                }
                
                // Update source statistics
                if (sourceStats) {
                    sourceStats.innerHTML = '';
                    const sourceData = data.data.by_source;
                    
                    if (Object.keys(sourceData).length > 0) {
                        Object.entries(sourceData).forEach(([source, count]) => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${source}</td>
                                <td>${count}</td>
                            `;
                            sourceStats.appendChild(row);
                        });
                    } else {
                        const row = document.createElement('tr');
                        row.innerHTML = '<td colspan="2" class="text-center">No data available</td>';
                        sourceStats.appendChild(row);
                    }
                }
                
                // Update agency statistics
                if (agencyStats) {
                    agencyStats.innerHTML = '';
                    const agencyData = data.data.by_agency;
                    
                    if (Object.keys(agencyData).length > 0) {
                        Object.entries(agencyData).forEach(([agency, count]) => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${agency}</td>
                                <td>${count}</td>
                            `;
                            agencyStats.appendChild(row);
                        });
                    } else {
                        const row = document.createElement('tr');
                        row.innerHTML = '<td colspan="2" class="text-center">No data available</td>';
                        agencyStats.appendChild(row);
                    }
                }
                
                // Update status statistics
                if (statusStats) {
                    statusStats.innerHTML = '';
                    const statusData = data.data.by_status;
                    
                    if (Object.keys(statusData).length > 0) {
                        Object.entries(statusData).forEach(([status, count]) => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td><span class="badge bg-${getStatusColor(status)}">${status}</span></td>
                                <td>${count}</td>
                            `;
                            statusStats.appendChild(row);
                        });
                    } else {
                        const row = document.createElement('tr');
                        row.innerHTML = '<td colspan="2" class="text-center">No data available</td>';
                        statusStats.appendChild(row);
                    }
                }
            })
            .catch(error => {
                console.error('Error loading statistics:', error);
                statsLoading.classList.add('d-none');
                
                // Show error message
                statsContent.innerHTML = `
                    <div class="alert alert-danger">
                        Error loading statistics: ${error.message}
                    </div>
                `;
                statsContent.classList.remove('d-none');
            });
    }
    
    // Function to get status color
    function getStatusColor(status) {
        switch (status) {
            case 'Active':
                return 'success';
            case 'Pending':
                return 'warning';
            case 'Completed':
                return 'info';
            case 'Cancelled':
                return 'danger';
            default:
                return 'secondary';
        }
    }
    
    // Function to show proposal details
    function showProposalDetails(proposal) {
        if (!modalTitle || !modalBody || !proposalModal) return;
        
        modalTitle.textContent = proposal.title || 'Proposal Details';
        
        // Format dates
        const releaseDate = proposal.release_date ? new Date(proposal.release_date).toLocaleDateString() : 'N/A';
        const dueDate = proposal.due_date ? new Date(proposal.due_date).toLocaleDateString() : 'N/A';
        
        // Build modal content
        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>ID:</strong> ${proposal.id}</p>
                    <p><strong>Source:</strong> ${proposal.source_name || 'N/A'}</p>
                    <p><strong>Agency:</strong> ${proposal.agency || 'N/A'}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${getStatusColor(proposal.status)}">${proposal.status || 'N/A'}</span></p>
                </div>
                <div class="col-md-6">
                    <p><strong>Release Date:</strong> ${releaseDate}</p>
                    <p><strong>Due Date:</strong> ${dueDate}</p>
                    <p><strong>NAICS Code:</strong> ${proposal.naics_code || 'N/A'}</p>
                    <p><strong>Set-Aside:</strong> ${proposal.set_aside || 'N/A'}</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h5>Description</h5>
                    <p>${proposal.description || 'No description available.'}</p>
                </div>
            </div>
        `;
        
        // Update view source button
        if (viewSourceButton) {
            if (proposal.url) {
                viewSourceButton.href = proposal.url;
                viewSourceButton.classList.remove('d-none');
            } else {
                viewSourceButton.classList.add('d-none');
            }
        }
        
        // Show the modal
        proposalModal.show();
    }
    
    // Function to render pagination
    function renderPagination(pagination) {
        if (!paginationElement || !pageInfoElement) return;
        
        // Clear existing pagination
        paginationElement.innerHTML = '';
        
        // Extract pagination data
        const page = parseInt(pagination.page) || 1;
        const perPage = parseInt(pagination.per_page) || 20;
        const totalCount = parseInt(pagination.total_count) || 0;
        const totalPages = parseInt(pagination.total_pages) || Math.ceil(totalCount / perPage);
        
        console.log('Rendering pagination:', { page, perPage, totalCount, totalPages });
        
        // Validate pagination data
        if (isNaN(page) || isNaN(perPage) || isNaN(totalCount) || isNaN(totalPages)) {
            console.error('Invalid pagination data:', { page, perPage, totalCount, totalPages });
            return;
        }
        
        // Update page info text
        const start = totalCount > 0 ? (page - 1) * perPage + 1 : 0;
        const end = Math.min(page * perPage, totalCount);
        pageInfoElement.textContent = `Showing ${start} to ${end} of ${totalCount} entries`;
        
        // Don't render pagination if there's only one page
        if (totalPages <= 1) {
            console.log('Not rendering pagination controls because totalPages <= 1');
            return;
        }
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${page <= 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" aria-label="Previous"><span aria-hidden="true">&laquo;</span></a>`;
        if (page > 1) {
            prevLi.querySelector('a').addEventListener('click', function(e) {
                e.preventDefault();
                currentState.page = page - 1;
                loadProposals();
            });
        }
        paginationElement.appendChild(prevLi);
        
        // Determine which page numbers to show
        let startPage = Math.max(1, page - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        
        // Adjust if we're near the end
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }
        
        // First page if not in range
        if (startPage > 1) {
            const firstLi = document.createElement('li');
            firstLi.className = 'page-item';
            firstLi.innerHTML = `<a class="page-link" href="#">1</a>`;
            firstLi.querySelector('a').addEventListener('click', function(e) {
                e.preventDefault();
                currentState.page = 1;
                loadProposals();
            });
            paginationElement.appendChild(firstLi);
            
            // Ellipsis if needed
            if (startPage > 2) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                ellipsisLi.innerHTML = `<a class="page-link" href="#">...</a>`;
                paginationElement.appendChild(ellipsisLi);
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === page ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            if (i !== page) {
                pageLi.querySelector('a').addEventListener('click', function(e) {
                    e.preventDefault();
                    currentState.page = i;
                    loadProposals();
                });
            }
            paginationElement.appendChild(pageLi);
        }
        
        // Last page if not in range
        if (endPage < totalPages) {
            // Ellipsis if needed
            if (endPage < totalPages - 1) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                ellipsisLi.innerHTML = `<a class="page-link" href="#">...</a>`;
                paginationElement.appendChild(ellipsisLi);
            }
            
            const lastLi = document.createElement('li');
            lastLi.className = 'page-item';
            lastLi.innerHTML = `<a class="page-link" href="#">${totalPages}</a>`;
            lastLi.querySelector('a').addEventListener('click', function(e) {
                e.preventDefault();
                currentState.page = totalPages;
                loadProposals();
            });
            paginationElement.appendChild(lastLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        
        // Ensure page and totalPages are numbers
        const pageNum = Number(page);
        const totalPagesNum = Number(totalPages);
        
        // Check if there are more pages
        const isNextDisabled = pageNum >= totalPagesNum;
        
        console.log('Next button disabled:', isNextDisabled, { 
            page: pageNum, 
            totalPages: totalPagesNum,
            'page === totalPages': pageNum === totalPagesNum,
            'page > totalPages': pageNum > totalPagesNum
        });
        
        nextLi.className = `page-item ${isNextDisabled ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" aria-label="Next"><span aria-hidden="true">&raquo;</span></a>`;
        
        if (pageNum < totalPagesNum) {
            nextLi.querySelector('a').addEventListener('click', function(e) {
                e.preventDefault();
                currentState.page = pageNum + 1;
                console.log('Navigating to next page:', currentState.page);
                loadProposals();
            });
        }
        
        paginationElement.appendChild(nextLi);
    }
}); 