document.addEventListener('DOMContentLoaded', () => {
    
    // --- Navigation Logic ---
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const targetId = item.getAttribute('data-target');
            views.forEach(v => v.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'view-queue') loadLibrary();
            if (targetId === 'view-activity') loadActivity();
            if (targetId === 'view-stats') {
                loadLibrary(); // Refresh storage
                loadStats();   // Fetch Tumblr API stats
            }
        });
    });

    // --- Toast Notifications ---
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fa-check-circle' : 'fa-circle-exclamation';
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        
        container.appendChild(toast);
        setTimeout(() => {
            if(toast.parentElement) toast.remove();
        }, 3000);
    }

    // --- Library / Queue Logic ---
    async function loadLibrary() {
        const container = document.getElementById('queue-container');
        try {
            const res = await fetch('/api/queue');
            const data = await res.json();
            
            // Update Storage Meter
            if (data.storage) {
                document.getElementById('storage-used').textContent = `${data.storage.used} MB`;
                document.getElementById('storage-fill').style.width = `${data.storage.percent}%`;
            }

            const categories = Object.keys(data.data);
            const datalist = document.getElementById('boards-list');
            if (datalist) datalist.innerHTML = categories.map(name => `<option value="${name}">`).join('');

            if (categories.length === 0) {
                container.innerHTML = '<div class="glass-card text-center"><p style="color:var(--text-muted)">Your library is empty.</p></div>';
                return;
            }

            container.innerHTML = '';
            for (const [category, count] of Object.entries(data.data)) {
                let percent = (count / 50) * 100; // 50 as scale
                if (percent > 100) percent = 100;
                
                let fillClass = '';
                if (count < 5) fillClass = 'empty';
                else if (count < 15) fillClass = 'low';

                const html = `
                    <div class="queue-item">
                        <div class="queue-header">
                            <span class="board-name">${category}</span>
                            <span class="image-count">${count} images</span>
                        </div>
                        <div class="progress-track">
                            <div class="progress-fill ${fillClass}" style="width: ${percent}%"></div>
                        </div>
                    </div>
                `;
                container.innerHTML += html;
            }
        } catch (e) {
            container.innerHTML = '<div class="glass-card text-center"><p class="text-danger">Sync error.</p></div>';
        }
    }

    // --- Add Content Logic ---
    const fileInput = document.getElementById('image-upload');
    const fileNameDisplay = document.getElementById('file-name');
    const previewContainer = document.getElementById('upload-preview-container');
    
    fileInput.addEventListener('change', (e) => {
        previewContainer.innerHTML = '';
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = `Selected: ${e.target.files.length} image(s)`;
            fileNameDisplay.style.display = 'block';
            
            // Generate previews
            Array.from(e.target.files).slice(0, 10).forEach(file => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    previewContainer.appendChild(img);
                }
                reader.readAsDataURL(file);
            });
            if (e.target.files.length > 10) {
                const more = document.createElement('div');
                more.style = 'display:flex; align-items:center; justify-content:center; font-size:0.8rem; color:var(--text-muted); background:rgba(255,255,255,0.05); border-radius:8px;';
                more.textContent = `+${e.target.files.length - 10}`;
                previewContainer.appendChild(more);
            }
        } else {
            fileNameDisplay.style.display = 'none';
        }
    });

    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('upload-btn');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';

        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('image', file);
        });
        formData.append('category_name', document.getElementById('board-select').value);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'success');
                fileInput.value = '';
                fileNameDisplay.style.display = 'none';
                previewContainer.innerHTML = '';
            } else {
                showToast(data.message, 'error');
            }
        } catch (err) {
            showToast('Connection error', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    document.getElementById('tags-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const categoryInput = document.getElementById('tag-category-select').value;
        const tagsInput = document.getElementById('category-tags-input').value;
        
        const btn = e.target.querySelector('button');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        try {
            const res = await fetch('/api/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category: categoryInput, tags: tagsInput })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Tags saved successfully', 'success');
                document.getElementById('category-tags-input').value = '';
            } else {
                showToast(data.message, 'error');
            }
        } catch (err) {
            showToast('Save failed', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    document.getElementById('titles-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const titlesInput = document.getElementById('title-phrases');
        try {
            const res = await fetch('/api/titles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ titles: titlesInput.value })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Captions saved', 'success');
                titlesInput.value = '';
            }
        } catch (err) {
            showToast('Save failed', 'error');
        }
    });

    // --- Activity & Sync Logic ---
    async function loadActivity() {
        const container = document.getElementById('activity-container');
        try {
            const res = await fetch('/api/activity');
            const data = await res.json();
            
            if (data.data.length === 0) {
                container.innerHTML = '<div class="glass-card text-center"><p style="color:var(--text-muted)">No recent activity.</p></div>';
                return;
            }

            container.innerHTML = '';
            data.data.forEach(item => {
                const isSuccess = item.status.toLowerCase() === 'queued';
                const iconClass = isSuccess ? 'success' : 'error';
                const iconName = isSuccess ? 'fa-check' : 'fa-xmark';
                
                const html = `
                    <div class="activity-item">
                        <div class="activity-icon ${iconClass}">
                            <i class="fa-solid ${iconName}"></i>
                        </div>
                        <div class="activity-details">
                            <h4>${item.title || item.filename}</h4>
                            <p>${item.category} • ${item.status}</p>
                            <span class="activity-time">${item.time}</span>
                        </div>
                    </div>
                `;
                container.innerHTML += html;
            });
        } catch (e) {
            container.innerHTML = '<div class="glass-card text-center"><p class="text-danger">Load error.</p></div>';
        }
    }

    document.getElementById('test-bot-btn').addEventListener('click', async () => {
        const btn = document.getElementById('test-bot-btn');
        const originalText = btn.innerHTML;
        try {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
            showToast('Syncing to Tumblr...', 'success');
            const res = await fetch(`/api/test_bot?token=${window.SYNC_TOKEN || ''}`, { method: 'POST' });
            const data = await res.json();
            showToast(data.message, 'success');
            setTimeout(loadActivity, 1000);
        } catch (e) {
            showToast('Sync failed', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    document.getElementById('clear-done-btn').addEventListener('click', async () => {
        if (!confirm('Permanently delete synced images?')) return;
        try {
            const res = await fetch('/api/clear_done', { method: 'POST' });
            const data = await res.json();
            showToast(data.message, 'success');
            loadLibrary(); // Refresh storage
        } catch (e) {
            showToast('Cleanup failed', 'error');
        }
    });

    // --- Stats & Command Center Logic ---
    async function loadStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            
            if (data.status === 'success' && data.data) {
                document.getElementById('stat-followers').textContent = data.data.followers.toLocaleString();
                document.getElementById('stat-posts').textContent = data.data.total_posts.toLocaleString();
                document.getElementById('stat-queue').textContent = data.data.queue_length;
            } else {
                document.getElementById('stat-followers').textContent = 'Error';
            }
        } catch (e) {
            console.error('Failed to load stats', e);
        }
    }

    // Initial load
    loadLibrary();
    loadStats();
});
