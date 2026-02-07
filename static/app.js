document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const resultsContainer = document.getElementById('results-container');
    const uploadContainer = document.getElementById('upload-container');
    const backToUploadBtn = document.getElementById('backToUploadBtn');

    let debounceTimer;

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if (query.length > 0) {
                if (uploadContainer) uploadContainer.style.display = 'none';
                if (resultsContainer) resultsContainer.style.display = 'block';

                debounceTimer = setTimeout(() => {
                    fetchData(query);
                }, 300);
            } else {
                if (uploadContainer) uploadContainer.style.display = 'block';
                if (resultsContainer) resultsContainer.style.display = 'none';
            }
        });
    }

    if (backToUploadBtn) {
        backToUploadBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (uploadContainer) uploadContainer.style.display = 'block';
            if (resultsContainer) resultsContainer.style.display = 'none';
        });
    }

    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const htmlElement = document.documentElement;

    function updateIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    }

    const currentTheme = localStorage.getItem('theme') || 'light';
    updateIcon(currentTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentAttr = htmlElement.getAttribute('data-theme');
            const newTheme = currentAttr === 'dark' ? 'light' : 'dark';

            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateIcon(newTheme);
        });
    }
});

async function fetchData(query) {
    try {
        const response = await fetch(`/view?search_query=${encodeURIComponent(query)}&format=json`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await response.json();
        renderResources(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function renderResources(data) {
    const resourcesList = document.getElementById('resources-list');
    if (!resourcesList) return;

    resourcesList.innerHTML = '';

    if (data.length === 0) {
        resourcesList.innerHTML = `
            <div class="col-12">
                <div class="text-center py-5 glass-panel">
                    <div class="mb-3 text-muted display-4"><i class="fa-regular fa-folder-open"></i></div>
                    <h3>No snippets found</h3>
                    <p class="text-muted">No matches found for that Roll Number.</p>
                </div>
            </div>
        `;
        return;
    }

    data.forEach(item => {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';

        let fileButton = '';
        if (item.file_path) {
            fileButton = `
                <div class="mt-3">
                     <a href="/uploads/${item.file_path}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill w-100">
                        <i class="fa-solid fa-download me-1"></i> Download File
                     </a>
                </div>
            `;
        }

        col.innerHTML = `
            <div class="card-snippet h-100 d-flex flex-column">
                <h5>${item.title}</h5>
                <p class="mb-1 text-muted text-small">
                    <i class="fa-solid fa-user-graduate me-1 text-primary opacity-75"></i> ${item.name}
                </p>
                 <p class="mb-2 text-muted text-small">
                    <i class="fa-solid fa-id-card me-1 text-secondary opacity-75"></i> ${item.roll_number}
                </p>
                <hr class="opacity-10 my-2">
                <p class="card-text flex-grow-1">${item.learning_content}</p>
                ${fileButton}
            </div>
        `;
        resourcesList.appendChild(col);
    });
}
