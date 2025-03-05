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
                // Hide loading indicator
                document.getElementById('collection-status-loading').classList.add('d-none');
                document.getElementById('collection-status-content').classList.remove('d-none');
                
                // Update the status message
                const statusMessage = document.getElementById('collection-status-message');
                const detailsContainer = document.getElementById('collection-details');
                
                if (data.success) {
                    statusMessage.textContent = 'Collection from all sources completed!';
                    statusMessage.parentElement.classList.remove('alert-danger');
                    statusMessage.parentElement.classList.add('alert-success');
                    
                    // Display collection details
                    detailsContainer.innerHTML = `
                        <p><strong>Sources processed:</strong> ${data.sources_processed}</p>
                        <p><strong>Total proposals collected:</strong> ${data.total_proposals_collected}</p>
                        <p><strong>Total collection time:</strong> ${data.total_collection_time} seconds</p>
                    `;
                    
                    // Reload the data sources to update the UI
                    loadDataSources();
                } else {
                    statusMessage.textContent = 'Collection failed!';
                    statusMessage.parentElement.classList.remove('alert-success');
                    statusMessage.parentElement.classList.add('alert-danger');
                    
                    // Display error details
                    detailsContainer.innerHTML = `
                        <p><strong>Error:</strong> ${data.error}</p>
                    `;
                }
            })
            .catch(error => {
                console.error('Error refreshing all sources:', error);
                
                // Hide loading indicator
                document.getElementById('collection-status-loading').classList.add('d-none');
                document.getElementById('collection-status-content').classList.remove('d-none');
                
                // Update the status message
                const statusMessage = document.getElementById('collection-status-message');
                statusMessage.textContent = 'Collection failed due to an error!';
                statusMessage.parentElement.classList.remove('alert-success');
                statusMessage.parentElement.classList.add('alert-danger');
                
                // Display error details
                document.getElementById('collection-details').innerHTML = `
                    <p><strong>Error:</strong> An unexpected error occurred. Please try again later.</p>
                `;
            });
        }
    });

    // Add event listener for checking all scrapers' health
    document.getElementById('refresh-all-sources').insertAdjacentHTML('afterend', 
        '<button id="check-all-health" class="btn btn-info ms-2">' +
        '<i class="bi bi-heart-pulse"></i> Check All Health</button>'
    );
    
    document.getElementById('check-all-health').addEventListener('click', function() {
        runHealthChecks();
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
        fetch('/api/sources').then(response => response.json()),
        fetch('/api/scraper-status').then(response => response.json())
    ])
    .then(([sourceData, healthData]) => {
        // Hide loading indicator
        document.getElementById('loading').classList.add('d-none');
        
        if (sourceData.sources && sourceData.sources.length > 0) {
            // Show sources container
            document.getElementById('sources-container').classList.remove('d-none');
            
            // Create a map of source ID to health status
            const healthMap = {};
            if (healthData.success && healthData.status) {
                healthData.status.forEach(status => {
                    healthMap[status.source_id] = status;
                });
            }
            
            // Populate the table
            const tableBody = document.getElementById('sources-table-body');
            tableBody.innerHTML = '';
            
            sourceData.sources.forEach(source => {
                const row = document.createElement('tr');
                
                // Get health status for this source
                const health = healthMap[source.id] || { status: 'unknown', last_checked: null };
                
                // Create status badge
                let statusBadge = '';
                if (health.status === 'working') {
                    statusBadge = '<span class="badge bg-success">Working</span>';
                } else if (health.status === 'not_working') {
                    statusBadge = '<span class="badge bg-danger">Not Working</span>';
                } else {
                    statusBadge = '<span class="badge bg-secondary">Unknown</span>';
                }
                
                // Add last checked time if available
                if (health.last_checked) {
                    const lastChecked = new Date(health.last_checked);
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
                if (source.last_collected) {
                    // Parse the ISO string as UTC and convert to local time
                    const lastCollected = new Date(source.last_collected);
                    const now = new Date();
                    
                    // Calculate time difference in local time
                    const diffTime = Math.abs(now - lastCollected);
                    const diffMinutes = Math.floor((diffTime % (1000 * 60 * 60)) / (1000 * 60));
                    const diffHours = Math.floor((diffTime % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                    
                    // Format the relative time text
                    if (diffDays > 0) {
                        lastCollectedText = `${diffDays} days, ${diffHours} hours ago`;
                    } else if (diffHours > 0) {
                        lastCollectedText = `${diffHours} hours, ${diffMinutes} minutes ago`;
                    } else {
                        lastCollectedText = `${diffMinutes} minutes ago`;
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
                    <td>${source.proposal_count || 0}</td>
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
        // Hide loading indicator
        document.getElementById('collection-status-loading').classList.add('d-none');
        document.getElementById('collection-status-content').classList.remove('d-none');
        
        // Update the status message
        const statusMessage = document.getElementById('collection-status-message');
        const detailsContainer = document.getElementById('collection-details');
        
        if (data.success) {
            statusMessage.textContent = 'Collection completed successfully!';
            statusMessage.parentElement.classList.remove('alert-danger');
            statusMessage.parentElement.classList.add('alert-success');
            
            // Display collection details
            detailsContainer.innerHTML = `
                <p><strong>Source:</strong> ${data.source_name}</p>
                <p><strong>Proposals collected:</strong> ${data.proposals_collected}</p>
                <p><strong>Collection time:</strong> ${data.collection_time} seconds</p>
            `;
            
            // Reload the data sources to update the UI
            loadDataSources();
        } else {
            statusMessage.textContent = 'Collection failed!';
            statusMessage.parentElement.classList.remove('alert-success');
            statusMessage.parentElement.classList.add('alert-danger');
            
            // Display error details
            detailsContainer.innerHTML = `
                <p><strong>Error:</strong> ${data.error}</p>
            `;
        }
    })
    .catch(error => {
        console.error('Error forcing collection:', error);
        
        // Hide loading indicator
        document.getElementById('collection-status-loading').classList.add('d-none');
        document.getElementById('collection-status-content').classList.remove('d-none');
        
        // Update the status message
        const statusMessage = document.getElementById('collection-status-message');
        statusMessage.textContent = 'Collection failed due to an error!';
        statusMessage.parentElement.classList.remove('alert-success');
        statusMessage.parentElement.classList.add('alert-danger');
        
        // Display error details
        document.getElementById('collection-details').innerHTML = `
            <p><strong>Error:</strong> An unexpected error occurred. Please try again later.</p>
        `;
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

// Add a function to run health checks for all scrapers
function runHealthChecks() {
    // Show loading indicator
    document.getElementById('loading-indicator').classList.remove('d-none');
    
    // Call the API to run health checks
    fetch('/api/scraper-status/check', {
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
            // Show success message in the notification area
            const notificationArea = document.getElementById('notification-area') || document.createElement('div');
            if (!document.getElementById('notification-area')) {
                notificationArea.id = 'notification-area';
                notificationArea.className = 'position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(notificationArea);
            }
            
            const toastId = 'health-toast-' + Date.now();
            notificationArea.innerHTML += `
                <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header bg-success text-white">
                        <strong class="me-auto">Health Checks</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="document.getElementById('${toastId}').remove()"></button>
                    </div>
                    <div class="toast-body">
                        Health checks started. The status will update shortly.
                    </div>
                </div>
            `;
            
            // Auto-remove toast after 5 seconds
            setTimeout(() => {
                const toast = document.getElementById(toastId);
                if (toast) toast.remove();
            }, 5000);
            
            // Reload the data sources after a short delay
            setTimeout(loadDataSources, 2000);
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
                        Error running health checks: ${data.error || 'Unknown error'}
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
        console.error('Error checking health:', error);
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
                    ${error.message || 'An error occurred while checking health.'}
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

// Add a function to check health for a specific scraper
function checkScraperHealth(sourceId) {
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
            // Show health status in a modal
            const modalId = 'health-modal-' + Date.now();
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}-label" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="${modalId}-label">Scraper Health Status</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <strong>Status:</strong> <span class="badge ${data.status === 'active' ? 'bg-success' : 'bg-warning'}">${data.status}</span>
                                </div>
                                <div class="mb-3">
                                    <strong>Last Run:</strong> ${data.last_run ? new Date(data.last_run).toLocaleString() : 'Never'}
                                </div>
                                <div class="mb-3">
                                    <strong>Next Run:</strong> ${data.next_run ? new Date(data.next_run).toLocaleString() : 'Not scheduled'}
                                </div>
                                <div class="mb-3">
                                    <strong>Message:</strong> ${data.message || 'No message'}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to the document
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer);
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
            
            // Remove modal from DOM when hidden
            document.getElementById(modalId).addEventListener('hidden.bs.modal', function () {
                document.body.removeChild(modalContainer);
            });
            
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
                        Error checking scraper health: ${data.error || 'Unknown error'}
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
        console.error('Error checking scraper health:', error);
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
                    ${error.message || 'An error occurred while checking scraper health.'}
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