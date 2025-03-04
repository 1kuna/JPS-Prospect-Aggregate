document.addEventListener('DOMContentLoaded', function() {
    // Load data sources when the page loads
    loadDataSources();

    // Set up event listeners
    document.getElementById('refresh-all-sources').addEventListener('click', function() {
        refreshAllSources();
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

    document.getElementById('refresh-data').addEventListener('click', function() {
        if (confirm('This will refresh all data from all sources. This may take some time. Are you sure you want to proceed?')) {
            refreshAllData();
        }
    });
    
    // Set up event listener for cleanup backups button
    document.getElementById('cleanup-backups').addEventListener('click', function() {
        cleanupBackups();
    });
});

function loadDataSources() {
    // Show loading indicator
    document.getElementById('loading').classList.remove('d-none');
    document.getElementById('sources-container').classList.add('d-none');
    document.getElementById('no-sources').classList.add('d-none');

    // Fetch data sources from the API
    fetch('/api/data-sources')
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            document.getElementById('loading').classList.add('d-none');
            
            if (data.sources && data.sources.length > 0) {
                // Show sources container
                document.getElementById('sources-container').classList.remove('d-none');
                
                // Populate the table
                const tableBody = document.getElementById('sources-table-body');
                tableBody.innerHTML = '';
                
                data.sources.forEach(source => {
                    const row = document.createElement('tr');
                    
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
                        <td>${lastCollectedText}</td>
                        <td>${source.proposal_count || 0}</td>
                        <td>
                            <button class="btn btn-sm btn-primary force-collect" data-source-id="${source.id}">
                                <i class="bi bi-arrow-repeat"></i> Force Re-collect
                            </button>
                        </td>
                    `;
                    
                    tableBody.appendChild(row);
                });
                
                // Add event listeners to the force collect buttons
                document.querySelectorAll('.force-collect').forEach(button => {
                    button.addEventListener('click', function() {
                        const sourceId = this.getAttribute('data-source-id');
                        forceCollect(sourceId);
                    });
                });
            } else {
                // Show no sources message
                document.getElementById('no-sources').classList.remove('d-none');
            }
        })
        .catch(error => {
            console.error('Error loading data sources:', error);
            document.getElementById('loading').classList.add('d-none');
            document.getElementById('no-sources').classList.remove('d-none');
            document.getElementById('no-sources').textContent = 'Error loading data sources. Please try again later.';
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

function refreshAllSources() {
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
    fetch('/api/init-db', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Database initialized successfully. The page will now reload.');
                window.location.reload();
            } else {
                alert('Error initializing database: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error initializing database:', error);
            alert('An unexpected error occurred while initializing the database. Please check the console for details.');
        });
}

function refreshAllData() {
    fetch('/api/refresh-data', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Data refreshed successfully. The page will now reload.');
                window.location.reload();
            } else {
                alert('Error refreshing data: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error refreshing data:', error);
            alert('An unexpected error occurred while refreshing data. Please check the console for details.');
        });
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