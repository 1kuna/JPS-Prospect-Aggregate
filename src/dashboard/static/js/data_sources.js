document.addEventListener('DOMContentLoaded', function() {
    // Load data sources when the page loads
    loadDataSources();

    // Set up event listeners
    document.getElementById('refresh-all-sources').addEventListener('click', function() {
        if (confirm('This will force re-collection from all data sources. This may take some time. Are you sure you want to proceed?')) {
            // Show collection status modal
            const collectionModal = new bootstrap.Modal(document.getElementById('collection-status-modal'));
            collectionModal.show();
            
            // Show loading indicator in the modal
            document.getElementById('collection-status-loading').classList.remove('d-none');
            document.getElementById('collection-status-content').classList.add('d-none');
            
            // Call the API to refresh all sources
            fetch('/api/data-sources/collect-all', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Start polling for task status
                    const taskId = data.task_id;
                    pollTaskStatus(taskId);
                } else {
                    // Handle error
                    showCollectionError(data.error || 'Unknown error');
                }
            })
            .catch(error => {
                console.error('Error starting collection:', error);
                showCollectionError('An unexpected error occurred. Please try again later.');
            });
        }
    });

    // Add event listener for checking all scrapers' health
    document.getElementById('refresh-all-sources').insertAdjacentHTML('afterend', 
        '<button id="check-all-health" class="btn btn-info ms-2">' +
        '<i class="bi bi-heart-pulse"></i> Check All Health</button>' +
        '<button id="initialize-status" class="btn btn-secondary ms-2">' +
        '<i class="bi bi-database-check"></i> Initialize Status</button>'
    );
    
    document.getElementById('check-all-health').addEventListener('click', function() {
        runHealthChecks();
    });
    
    document.getElementById('initialize-status').addEventListener('click', function() {
        initializeScraperStatus();
    });

    // Set up event listeners for database operations
    document.getElementById('rebuild-db').addEventListener('click', function() {
        if (confirm('WARNING: This will delete and rebuild the entire database. All data will be lost and then re-collected. This operation cannot be undone. Are you sure you want to proceed?')) {
            rebuildDatabase();
        }
    });

    document.getElementById('init-db').addEventListener('click', function() {
        if (confirm('WARNING: This will initialize the database. If the database already exists, this operation will have no effect. Are you sure you want to proceed?')) {
            initializeDatabase();
        }
    });
    
    document.getElementById('manage-backups').addEventListener('click', function() {
        openBackupsModal();
    });
    
    document.getElementById('reset-everything').addEventListener('click', function() {
        resetEverything();
    });

    // Set up event listener for cleanup backups button
    document.getElementById('cleanup-backups').addEventListener('click', function() {
        cleanupBackups();
    });

    // Add event listener for statistics modal
    const statsModal = document.getElementById('stats-modal');
    if (statsModal) {
        statsModal.addEventListener('show.bs.modal', function() {
            loadStatistics();
        });
    }
});

function loadDataSources() {
    // Show loading indicator
    document.getElementById('loading').classList.remove('d-none');
    document.getElementById('sources-container').classList.add('d-none');
    document.getElementById('no-sources').classList.add('d-none');

    // Fetch data sources and health status from the API
    Promise.all([
        fetch('/api/data-sources').then(response => response.json()),
        fetch('/api/scraper-status').then(response => response.json())
    ])
    .then(([sourcesData, healthData]) => {
        // Hide loading indicator
        document.getElementById('loading').classList.add('d-none');
        
        if (sourcesData && sourcesData.length > 0) {
            // Show sources container
            document.getElementById('sources-container').classList.remove('d-none');
            
            // Create a map of source ID to health status
            const healthMap = {};
            if (Array.isArray(healthData)) {
                healthData.forEach(status => {
                    healthMap[status.source_id] = status;
                });
            }
            
            // Populate the table
            const tableBody = document.getElementById('sources-table-body');
            tableBody.innerHTML = '';
            
            sourcesData.forEach(source => {
                const row = document.createElement('tr');
                
                // Get health status for this source
                const health = healthMap[source.id] || { status: 'unknown', last_checked: null };
                
                // Create status badge based on source.status from the data-sources endpoint
                let statusBadge = '';
                if (source.status === 'working') {
                    statusBadge = '<span class="badge bg-success">Working</span>';
                } else if (source.status === 'not_working') {
                    statusBadge = '<span class="badge bg-danger">Not Working</span>';
                } else {
                    statusBadge = '<span class="badge bg-secondary">Unknown</span>';
                }
                
                // Add last checked time if available
                if (source.lastChecked) {
                    const lastChecked = new Date(source.lastChecked);
                    const options = { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: true
                    };
                    statusBadge += `<br><small class="text-muted">Last checked: ${lastChecked.toLocaleString(undefined, options)}</small>`;
                }
                
                // Format the last collected date
                let lastCollectedText = 'Never';
                if (source.lastScraped) {
                    // Parse the ISO string as UTC and convert to local time
                    const lastCollected = new Date(source.lastScraped);
                    const now = new Date();
                    
                    // Calculate time difference in milliseconds
                    const diffTime = Math.abs(now - lastCollected);
                    
                    // Calculate time components
                    const diffMinutes = Math.floor((diffTime / (1000 * 60)) % 60);
                    const diffHours = Math.floor((diffTime / (1000 * 60 * 60)) % 24);
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                    
                    // Format the relative time text
                    if (diffDays > 0) {
                        lastCollectedText = `${diffDays} day${diffDays > 1 ? 's' : ''}, ${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
                    } else if (diffHours > 0) {
                        lastCollectedText = `${diffHours} hour${diffHours > 1 ? 's' : ''}, ${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
                    } else if (diffMinutes > 0) {
                        lastCollectedText = `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
                    } else {
                        lastCollectedText = `Just now`;
                    }
                    
                    // Format the exact timestamp in local time
                    const options = { 
                        year: 'numeric', 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: true
                    };
                    
                    lastCollectedText += `<br><small class="text-muted">${lastCollected.toLocaleString(undefined, options)}</small>`;
                }
                
                // Create the row content
                row.innerHTML = `
                    <td>${source.id}</td>
                    <td>${source.name}</td>
                    <td><a href="${source.url}" target="_blank">${source.url}</a></td>
                    <td>${source.description || 'N/A'}</td>
                    <td>${statusBadge}</td>
                    <td>${lastCollectedText}</td>
                    <td>${source.proposalCount || 0}</td>
                    <td>
                        <div class="btn-group">
                            <button class="btn btn-sm btn-primary force-collect" data-source-id="${source.id}">
                                <i class="bi bi-arrow-repeat"></i> Force Re-collect
                            </button>
                            <button class="btn btn-sm btn-info check-health" data-source-id="${source.id}">
                                <i class="bi bi-heart-pulse"></i> Check Health
                            </button>
                        </div>
                    </td>
                `;
                
                tableBody.appendChild(row);
            });
            
            // Add event listeners to the buttons
            document.querySelectorAll('.force-collect').forEach(button => {
                button.addEventListener('click', function() {
                    const sourceId = this.getAttribute('data-source-id');
                    forceCollect(sourceId);
                });
            });
            
            document.querySelectorAll('.check-health').forEach(button => {
                button.addEventListener('click', function() {
                    const sourceId = this.getAttribute('data-source-id');
                    checkScraperHealth(sourceId);
                });
            });
        } else {
            // Show no sources message
            document.getElementById('no-sources').classList.remove('d-none');
        }
    })
    .catch(error => {
        console.error('Error loading data:', error);
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('no-sources').classList.remove('d-none');
        document.getElementById('no-sources').textContent = 'Error loading data. Please try again later.';
    });
}

function forceCollect(sourceId) {
    // Show collection status modal
    const collectionModal = new bootstrap.Modal(document.getElementById('collection-status-modal'));
    collectionModal.show();
    
    // Show loading indicator in the modal
    document.getElementById('collection-status-loading').classList.remove('d-none');
    document.getElementById('collection-status-content').classList.add('d-none');
    
    // Call the API to force collect from the source
    fetch(`/api/data-sources/${sourceId}/collect`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Start polling for task status
            const taskId = data.task_id;
            const sourceName = data.source_name;
            pollSourceTaskStatus(taskId, sourceName);
        } else {
            // Handle error
            showCollectionError(data.error || 'Unknown error');
        }
    })
    .catch(error => {
        console.error('Error starting collection:', error);
        showCollectionError('An unexpected error occurred. Please try again later.');
    });
}

// Function to poll source task status
function pollSourceTaskStatus(taskId, sourceName, interval = 2000) {
    // Check task status
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.status === 'completed') {
                    // Task completed successfully
                    const result = data.result;
                    
                    // Hide loading indicator
                    document.getElementById('collection-status-loading').classList.add('d-none');
                    document.getElementById('collection-status-content').classList.remove('d-none');
                    
                    // Update the status message
                    const statusMessage = document.getElementById('collection-status-message');
                    const detailsContainer = document.getElementById('collection-details');
                    
                    statusMessage.textContent = 'Collection completed successfully!';
                    statusMessage.parentElement.classList.remove('alert-danger');
                    statusMessage.parentElement.classList.add('alert-success');
                    
                    // Display collection details
                    detailsContainer.innerHTML = `
                        <p><strong>Source:</strong> ${sourceName}</p>
                        <p><strong>Proposals collected:</strong> ${result.proposals_collected || 0}</p>
                        <p><strong>Collection time:</strong> ${result.collection_time ? result.collection_time.toFixed(2) : 0} seconds</p>
                    `;
                    
                    // Reload the data sources to update the UI
                    loadDataSources();
                } else if (data.status === 'failed') {
                    // Task failed
                    showCollectionError(data.error || 'Task failed');
                } else {
                    // Task still in progress, continue polling
                    setTimeout(() => pollSourceTaskStatus(taskId, sourceName, interval), interval);
                }
            } else {
                // Error checking task status
                showCollectionError(data.error || 'Error checking task status');
            }
        })
        .catch(error => {
            console.error('Error checking task status:', error);
            showCollectionError('Error checking task status');
        });
}

function refreshSource(sourceId) {
    // Show loading indicator
    document.getElementById('loading-indicator').classList.remove('d-none');
    
    // Call the API to check the scraper's health
    fetch(`/api/scraper-status/${sourceId}`, {
        method: 'GET'
    })
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
        document.getElementById('loading-indicator').classList.add('d-none');
        
        if (data.status) {
            // Show success message in a toast or notification area
            const notificationArea = document.getElementById('notification-area') || document.createElement('div');
            if (!document.getElementById('notification-area')) {
                notificationArea.id = 'notification-area';
                notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(notificationArea);
            }
            
            const toastId = 'refresh-toast-' + Date.now();
            notificationArea.innerHTML += `
                <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header bg-success text-white">
                        <strong class="me-auto">Source Refreshed</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                    </div>
                    <div class="toast-body">
                        Current status: ${data.status}
                    </div>
                </div>
            `;
            
            // Auto-remove toast after 5 seconds
            setTimeout(() => {
                const toast = document.getElementById(toastId);
                if (toast) toast.remove();
            }, 5000);
            
            // Reload the data sources
            loadDataSources();
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
                        Error refreshing source: ${data.error || 'Unknown error'}
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
        console.error('Error refreshing source:', error);
        document.getElementById('loading-indicator').classList.add('d-none');
        
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
                    ${error.message || 'An error occurred while refreshing the source.'}
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

function rebuildDatabase() {
    fetch('/api/rebuild-db', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Database rebuilt successfully. The page will now reload.');
                window.location.reload();
            } else {
                alert('Error rebuilding database: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error rebuilding database:', error);
            alert('An unexpected error occurred while rebuilding the database. Please check the console for details.');
        });
}

function initializeDatabase() {
    // Create a detailed warning message
    const warningMessage = 
        'WARNING: This will delete the current database and create a new one!\n\n' +
        'This operation will:\n' +
        '1. Delete ALL existing data\n' +
        '2. Create a new empty database\n' +
        '3. Initialize the data sources\n\n' +
        'This operation cannot be undone. All your data will be permanently lost.\n\n' +
        'Are you absolutely sure you want to proceed?';
        
    if (confirm(warningMessage)) {
        // Double-check with a second confirmation
        if (confirm('FINAL WARNING: You are about to delete ALL data. This cannot be undone. Type "INIT" to confirm.')) {
            // Show loading indicator
            const loadingIndicator = document.getElementById('loading-indicator');
            loadingIndicator.classList.remove('d-none');
            
            fetch('/api/init-db', { method: 'POST' })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Hide loading indicator
                    loadingIndicator.classList.add('d-none');
                    
                    if (data.success) {
                        alert('Database initialized successfully. The page will now reload.');
                        window.location.reload();
                    } else {
                        const errorMessage = data.error || 'An unknown error occurred';
                        console.error('Database initialization error:', errorMessage);
                        alert('Error initializing database: ' + errorMessage + '\n\nPlease check the browser console (F12) for more details.');
                    }
                })
                .catch(error => {
                    // Hide loading indicator
                    loadingIndicator.classList.add('d-none');
                    
                    console.error('Error initializing database:', error);
                    alert('An unexpected error occurred while initializing the database.\n\nError details: ' + error.message + '\n\nPlease check the browser console (F12) for more details.');
                });
        }
    }
}

// Function to open the backups modal and load the backups
function openBackupsModal() {
    // Show the modal
    const backupsModal = new bootstrap.Modal(document.getElementById('backupsModal'));
    backupsModal.show();
    
    // Load the backups
    loadBackups();
}

// Function to load the database backups
function loadBackups() {
    const backupsTableBody = document.getElementById('backups-table-body');
    
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
    const maxBackupsInput = document.getElementById('max-backups');
    const loadingIndicator = document.getElementById('loading-indicator');
    
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
            loadBackups();
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

// Function to reset everything (downloads and database)
function resetEverything() {
    const loadingIndicator = document.getElementById('loading-indicator');
    
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

// Helper function to show toast notifications
function showToast(title, message, type = 'info') {
    // Get or create notification area
    const notificationArea = document.getElementById('notification-area') || document.createElement('div');
    if (!document.getElementById('notification-area')) {
        notificationArea.id = 'notification-area';
        notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(notificationArea);
    }
    
    // Create a unique ID for this toast
    const toastId = 'toast-' + Date.now();
    
    // Create toast HTML
    const toastHtml = `
        <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} ${type === 'warning' || type === 'info' ? 'text-dark' : 'text-white'}">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to notification area
    notificationArea.innerHTML += toastHtml;
    
    // Auto-remove toast after 5 seconds
    setTimeout(() => {
        const toast = document.getElementById(toastId);
        if (toast) toast.remove();
    }, 5000);
}

// Function to run health checks for all scrapers
function runHealthChecks() {
    // Show loading indicator
    document.getElementById('loading-indicator').classList.remove('d-none');
    
    // First get all data sources
    fetch('/api/data-sources')
        .then(response => response.json())
        .then(sources => {
            if (!sources || sources.length === 0) {
                throw new Error('No data sources found');
            }
            
            // Create an array of promises for each health check
            const healthCheckPromises = sources.map(source => 
                fetch(`/api/scraper-status/${source.id}/check`, {
                    method: 'POST'
                }).then(response => response.json())
                .then(result => {
                    // Add source name to the result
                    result.sourceName = source.name;
                    return result;
                })
            );
            
            // Wait for all health checks to complete
            return Promise.all(healthCheckPromises);
        })
        .then(results => {
            // Hide loading indicator
            document.getElementById('loading-indicator').classList.add('d-none');
            
            // Count successes and failures
            const successes = results.filter(result => result.success && result.status === 'working').length;
            const failures = results.filter(result => result.success && result.status === 'not_working').length;
            const errors = results.filter(result => !result.success).length;
            
            // Create a detailed message
            let detailedMessage = `<strong>Results:</strong> ${successes} working, ${failures} not working, ${errors} errors.<br><br>`;
            
            // Add details for each source
            results.forEach(result => {
                if (result.success) {
                    const statusClass = result.status === 'working' ? 'text-success' : 'text-danger';
                    const statusText = result.status === 'working' ? 'Working' : 'Not Working';
                    const responseTime = result.response_time ? `${result.response_time.toFixed(2)}s` : 'N/A';
                    
                    detailedMessage += `<strong>${result.sourceName}:</strong> <span class="${statusClass}">${statusText}</span> (${responseTime})<br>`;
                } else {
                    detailedMessage += `<strong>${result.sourceName}:</strong> <span class="text-danger">Error: ${result.error || 'Unknown error'}</span><br>`;
                }
            });
            
            // Show summary toast
            showToast(
                'Health Checks Completed', 
                detailedMessage, 
                successes === results.length ? 'success' : (failures > 0 ? 'warning' : 'danger')
            );
            
            // Reload the data sources to show updated status
            loadDataSources();
        })
        .catch(error => {
            // Hide loading indicator
            document.getElementById('loading-indicator').classList.add('d-none');
            
            // Show error toast
            showToast('Health Check Error', error.message, 'danger');
        });
}

// Add a function to check health for a specific scraper
function checkScraperHealth(sourceId) {
    // Show loading indicator
    document.getElementById('loading-indicator').classList.remove('d-none');
    
    // Call the API to check the scraper's health
    fetch(`/api/scraper-status/${sourceId}/check`, {
        method: 'POST'
    })
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
        document.getElementById('loading-indicator').classList.add('d-none');
        
        if (data.success) {
            // Show success toast with status information
            const statusText = data.status === 'working' ? 'Working' : 'Not Working';
            const responseTime = data.response_time ? `${data.response_time.toFixed(2)}s` : 'N/A';
            
            showToast(
                'Health Check Complete', 
                `Status: <strong>${statusText}</strong><br>Response Time: ${responseTime}<br>The page will refresh to show the updated status.`, 
                data.status === 'working' ? 'success' : 'warning'
            );
            
            // Reload the data sources after a short delay to show the updated status
            setTimeout(() => {
                loadDataSources();
            }, 2000);
        } else {
            // Show error toast
            showToast('Health check failed', data.error || 'An error occurred while checking health.', 'danger');
        }
    })
    .catch(error => {
        // Hide loading indicator
        document.getElementById('loading-indicator').classList.add('d-none');
        
        // Show error toast
        showToast('Health check failed', error.message, 'danger');
    });
}

// Function to load statistics
function loadStatistics() {
    // Get the elements
    const statsLoading = document.getElementById('stats-loading');
    const statsContent = document.getElementById('stats-content');
    
    // Show loading indicator
    statsLoading.classList.remove('d-none');
    statsContent.classList.add('d-none');
    
    // Fetch statistics - on the data sources page, we want to see all proposals
    fetch('/api/statistics?only_latest=false')
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || `HTTP error! Status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            // Create the statistics content
            let html = `
                <h4>Total Proposals: <span class="badge bg-primary">${data.total_proposals}</span></h4>
                
                <div class="row mt-4">
                    <div class="col-md-4">
                        <h5>By Source</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Source</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            // Add source stats
            Object.entries(data.by_source).forEach(([name, count]) => {
                html += `
                    <tr>
                        <td>${name}</td>
                        <td>${count}</td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="col-md-4">
                        <h5>By Agency</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Agency</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            // Add agency stats
            Object.entries(data.by_agency).forEach(([agency, count]) => {
                html += `
                    <tr>
                        <td>${agency}</td>
                        <td>${count}</td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="col-md-4">
                        <h5>By Status</h5>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Status</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            // Add status stats
            Object.entries(data.by_status).forEach(([status, count]) => {
                html += `
                    <tr>
                        <td>${status}</td>
                        <td>${count}</td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="alert alert-info mt-3">
                    Note: Statistics are showing all proposals, including historical versions.
                </div>
            `;
            
            // Update the content
            statsContent.innerHTML = html;
            
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

// Function to poll task status
function pollTaskStatus(taskId, interval = 2000) {
    // Check task status
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.status === 'completed') {
                    // Task completed successfully
                    const result = data.result;
                    
                    // Hide loading indicator
                    document.getElementById('collection-status-loading').classList.add('d-none');
                    document.getElementById('collection-status-content').classList.remove('d-none');
                    
                    // Update the status message
                    const statusMessage = document.getElementById('collection-status-message');
                    const detailsContainer = document.getElementById('collection-details');
                    
                    statusMessage.textContent = 'Collection from all sources completed!';
                    statusMessage.parentElement.classList.remove('alert-danger');
                    statusMessage.parentElement.classList.add('alert-success');
                    
                    // Display collection details
                    detailsContainer.innerHTML = `
                        <p><strong>Sources processed:</strong> ${result.results ? result.results.length : 0}</p>
                        <p><strong>Total proposals collected:</strong> ${result.proposals_collected || 0}</p>
                        <p><strong>Total collection time:</strong> ${result.collection_time ? result.collection_time.toFixed(2) : 0} seconds</p>
                    `;
                    
                    // Reload the data sources to update the UI
                    loadDataSources();
                } else if (data.status === 'failed') {
                    // Task failed
                    showCollectionError(data.error || 'Task failed');
                } else {
                    // Task still in progress, continue polling
                    setTimeout(() => pollTaskStatus(taskId, interval), interval);
                }
            } else {
                // Error checking task status
                showCollectionError(data.error || 'Error checking task status');
            }
        })
        .catch(error => {
            console.error('Error checking task status:', error);
            showCollectionError('Error checking task status');
        });
}

// Function to show collection error
function showCollectionError(errorMessage) {
    // Hide loading indicator
    document.getElementById('collection-status-loading').classList.add('d-none');
    document.getElementById('collection-status-content').classList.remove('d-none');
    
    // Update the status message
    const statusMessage = document.getElementById('collection-status-message');
    statusMessage.textContent = 'Collection failed!';
    statusMessage.parentElement.classList.remove('alert-success');
    statusMessage.parentElement.classList.add('alert-danger');
    
    // Display error details
    document.getElementById('collection-details').innerHTML = `
        <p><strong>Error:</strong> ${errorMessage}</p>
    `;
}

// Function to initialize scraper status for all data sources
function initializeScraperStatus() {
    // Show loading indicator
    document.getElementById('loading-indicator').classList.remove('d-none');
    
    // Call the API to initialize scraper status
    fetch('/api/scraper-status/initialize', {
        method: 'POST'
    })
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
        document.getElementById('loading-indicator').classList.add('d-none');
        
        if (data.success) {
            // Show success toast
            showToast('Status Initialized', data.message, 'success');
            
            // Reload the data sources to show the updated status
            loadDataSources();
        } else {
            // Show error toast
            showToast('Initialization Failed', data.error || 'An error occurred while initializing status.', 'danger');
        }
    })
    .catch(error => {
        // Hide loading indicator
        document.getElementById('loading-indicator').classList.add('d-none');
        
        // Show error toast
        showToast('Initialization Failed', error.message, 'danger');
    });
} 