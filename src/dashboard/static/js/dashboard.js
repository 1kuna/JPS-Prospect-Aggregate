// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Pagination functionality
    function setupPagination() {
        const paginationContainer = document.getElementById('pagination');
        if (!paginationContainer) return;

        // Center the pagination container
        const navElement = paginationContainer.closest('nav');
        if (navElement) {
            const containerDiv = navElement.querySelector('.d-flex');
            if (containerDiv) {
                containerDiv.classList.remove('justify-content-between');
                containerDiv.classList.add('justify-content-center');
                
                // Adjust the layout to be grid-based for better centering
                containerDiv.style.display = 'grid';
                containerDiv.style.gridTemplateColumns = '1fr auto 1fr';
                containerDiv.style.alignItems = 'center';
                containerDiv.style.gap = '1rem';
            }
        }

        // Function to render pagination with only Previous and Next buttons
        window.renderPagination = function(currentPage, totalPages) {
            if (!paginationContainer) return;
            
            paginationContainer.innerHTML = '';
            
            // Previous button
            const prevLi = document.createElement('li');
            prevLi.className = 'page-item' + (currentPage <= 1 ? ' disabled' : '');
            
            const prevLink = document.createElement('a');
            prevLink.className = 'page-link';
            prevLink.href = '#';
            prevLink.setAttribute('aria-label', 'Previous');
            prevLink.innerHTML = '<span aria-hidden="true">&laquo;</span> Previous';
            
            if (currentPage > 1) {
                prevLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (window.loadProposals) {
                        window.loadProposals(currentPage - 1);
                    }
                });
            }
            
            prevLi.appendChild(prevLink);
            paginationContainer.appendChild(prevLi);
            
            // Page indicator (current page / total pages)
            const pageLi = document.createElement('li');
            pageLi.className = 'page-item disabled';
            
            const pageSpan = document.createElement('span');
            pageSpan.className = 'page-link';
            pageSpan.textContent = `Page ${currentPage} of ${totalPages}`;
            
            pageLi.appendChild(pageSpan);
            paginationContainer.appendChild(pageLi);
            
            // Next button
            const nextLi = document.createElement('li');
            nextLi.className = 'page-item' + (currentPage >= totalPages ? ' disabled' : '');
            
            const nextLink = document.createElement('a');
            nextLink.className = 'page-link';
            nextLink.href = '#';
            nextLink.setAttribute('aria-label', 'Next');
            nextLink.innerHTML = 'Next <span aria-hidden="true">&raquo;</span>';
            
            if (currentPage < totalPages) {
                nextLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (window.loadProposals) {
                        window.loadProposals(currentPage + 1);
                    }
                });
            }
            
            nextLi.appendChild(nextLink);
            paginationContainer.appendChild(nextLi);
            
            // Update page info
            const pageInfo = document.getElementById('page-info');
            if (pageInfo) {
                pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
            }
        };
        
        // Initial render with default values
        window.renderPagination(1, 1);
    }

    // Initialize pagination
    setupPagination();
}); 