// Initialize Socket.IO connection
const socket = io();

let sessionId = null;
let isConnected = false;

// Define a threshold for pasted content (e.g., 10,000 lines for combo, 5,000 for proxy)
const PASTE_LINE_LIMIT_COMBO = 10000;
const PASTE_LINE_LIMIT_PROXY = 5000;

// Status message system
function showStatusMessage(message, type = 'info') {
    const statusContainer = document.getElementById('status-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `status-message ${type}`;
    messageDiv.textContent = message;

    statusContainer.appendChild(messageDiv);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    statusContainer.removeChild(messageDiv);
                }
            }, 300);
        }
    }, 5000);
}

// Socket event handlers
socket.on('connect', () => {
    isConnected = true;
    showStatusMessage('Connected to server successfully!', 'success');
    // Request session ID from server if not already present in local storage
    const storedSessionId = localStorage.getItem('sessionId');
    if (storedSessionId) {
        socket.emit('reconnect_session', { session_id: storedSessionId });
    } else {
        socket.emit('request_session'); // Request a new session if none stored
    }
});

socket.on('disconnect', () => {
    isConnected = false;
    showStatusMessage('Disconnected from server!', 'error');
    // No need to update button states here, as they are always enabled
});

socket.on('session_created', (data) => {
    sessionId = data.session_id;
    localStorage.setItem('sessionId', sessionId); // Store session ID in local storage
    console.log(`Session created: ${sessionId}`);
    showStatusMessage('Session created successfully!', 'success');
    // Update URL with session ID (client-side only, won't persist across full page loads without server support)
    history.pushState({ sessionId: sessionId }, '', `?session=${sessionId}`);
    // Reset textarea content and stats display for a new session
    document.getElementById('combo-input').value = '';
    document.getElementById('proxy-input').value = '';
    updateStatsDisplay({ // Reset stats to initial state
        status: '❌ STOPPED',
        total_lines: 0,
        checked: 0,
        invalid: 0,
        hits: 0,
        custom: 0,
        total_mega_fan: 0,
        total_fan_member: 0,
        total_ultimate_mega: 0,
        errors: 0,
        retries: 0,
        cpm: 0,
        elapsed_time: '0:00:00'
    });
    // Buttons are always enabled, so no updateButtonStates call needed here
});

socket.on('session_reconnected', (data) => {
    sessionId = data.session_id;
    console.log(`Session reconnected: ${sessionId}`);
    showStatusMessage('Session reconnected successfully!', 'success');
    // Update URL with session ID
    history.pushState({ sessionId: sessionId }, '', `?session=${sessionId}`);
    // Load previous state if the server sends it
    if (data.previous_state) {
        updateStatsDisplay(data.previous_state.stats);
        // Indicate if files were uploaded, but don't populate textareas with full content
        document.getElementById('combo-input').value = data.previous_state.combo_file_uploaded ? `Combo file uploaded (${data.previous_state.stats.total_lines} lines). Ready to check. ✅` : '';
        document.getElementById('proxy-input').value = data.previous_state.proxy_file_uploaded ? `Proxy file uploaded. Ready to check. ✅` : '';
        document.getElementById('threads-input').value = data.previous_state.threads || 10;
        document.getElementById('proxy-type-select').value = data.previous_state.proxy_type || 'http';
        
        // No need to update button states here, as they are always enabled
        // updateButtonStates(data.previous_state.checker_status); // REMOVED

        // Trigger textarea auto-resize after populating content (for the placeholder text)
        const textareas = document.querySelectorAll('.upload-textarea');
        textareas.forEach(textarea => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
        });
    }
});

// Handle stats update
socket.on('stats_update', (data) => {
    updateStatsDisplay(data);
});

// Handle errors
socket.on('error', (data) => {
    showStatusMessage(data.message, 'error');
});

// Handle combo uploaded (from server after HTTP POST or WebSocket)
socket.on('combo_uploaded', (data) => {
    showStatusMessage(data.message, 'success');
    // Update total lines immediately
    document.getElementById('total-lines').textContent = data.count;
    document.getElementById('combo-input').value = `Combo file uploaded (${data.count} lines). Ready to check. ✅`;
    // Trigger textarea auto-resize
    const textarea = document.getElementById('combo-input');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
});

// Handle proxy uploaded (from server after HTTP POST or WebSocket)
socket.on('proxy_uploaded', (data) => {
    showStatusMessage(data.message, 'success');
    document.getElementById('proxy-input').value = `Proxy file uploaded (${data.count} lines). Ready to check. ✅`;
    document.getElementById('proxy-type-select').value = data.proxy_type;
    // Trigger textarea auto-resize
    const textarea = document.getElementById('proxy-input');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
});

// Handle checker started
socket.on('checker_started', (data) => {
    showStatusMessage(data.message, 'success');
    // No need to update button states here, as they are always enabled
});

// Handle checker stopped
socket.on('checker_stopped', (data) => {
    showStatusMessage(data.message, 'info');
    // No need to update button states here, as they are always enabled
});

// Handle checker paused
socket.on('checker_paused', (data) => {
    showStatusMessage(data.message, 'info');
    // No need to update button states here, as they are always enabled
});

// Handle checker continued
socket.on('checker_continued', (data) => {
    showStatusMessage(data.message, 'success');
    // No need to update button states here, as they are always enabled
});

// Handle checker completed
socket.on('checker_completed', (data) => {
    showStatusMessage(data.message, 'success');
    // No need to update button states here, as they are always enabled
});

// Handle hits available
socket.on('hits_available', (data) => {
    showStatusMessage('Hits file is ready for download!', 'success');
    downloadFile(data.content, data.filename);
});

// Handle hits download
socket.on('hits_download', (data) => {
    downloadFile(data.content, data.filename);
    showStatusMessage('Hits downloaded successfully!', 'success');
});

// Update stats display
function updateStatsDisplay(data) {
    document.getElementById('status').textContent = data.status;
    document.getElementById('total-lines').textContent = data.total_lines;
    document.getElementById('checked').textContent = data.checked;
    document.getElementById('invalid').textContent = data.invalid;
    document.getElementById('hits').textContent = data.hits;
    document.getElementById('custom').textContent = data.custom;
    document.getElementById('total-mega-fan').textContent = data.total_mega_fan;
    document.getElementById('total-fan-member').textContent = data.total_fan_member;
    document.getElementById('total-ultimate-mega').textContent = data.total_ultimate_mega;
    document.getElementById('errors').textContent = data.errors;
    document.getElementById('retries').textContent = data.retries;
    document.getElementById('cpm').textContent = data.cpm;
    document.getElementById('elapsed-time').textContent = data.elapsed_time;

    // Update status color based on status
    const statusElement = document.getElementById('status');
    if (data.status.includes('RUNNING')) {
        statusElement.style.color = '#4ecdc4';
    } else if (data.status.includes('PAUSED')) {
        statusElement.style.color = '#feca57';
    } else if (data.status.includes('COMPLETE')) {
        statusElement.style.color = '#4ecdc4';
    } else {
        statusElement.style.color = '#ff6b6b';
    }
}

// Removed updateButtonStates function as buttons will always be enabled.
// function updateButtonStates(state) { ... }

// Download file function
function downloadFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Validate session
function validateSession() {
    if (!sessionId) {
        showStatusMessage('No active session. Please refresh the page or wait for connection.', 'error');
        return false;
    }
    if (!isConnected) {
        showStatusMessage('Not connected to server. Please check your connection.', 'error');
        return false;
    }
    return true;
}

// Function to handle file upload via HTTP POST (for large files via file dialog)
function uploadFileViaHttp(file, fileType) {
    if (!validateSession()) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    formData.append('file_type', fileType);
    if (fileType === 'proxy') {
        formData.append('proxy_type', document.getElementById('proxy-type-select').value);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload_file', true); // Use the new HTTP POST route

    xhr.onload = function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            // Server will emit success via SocketIO, so no need to show message here
            console.log(`${fileType} upload success:`, response.message);
        } else {
            const errorResponse = JSON.parse(xhr.responseText);
            showStatusMessage(`Error uploading ${fileType}: ${errorResponse.message}`, 'error');
            console.error(`Error uploading ${fileType}:`, errorResponse);
            // Clear textarea if HTTP upload failed
            if (fileType === 'combo') document.getElementById('combo-input').value = '';
            if (fileType === 'proxy') document.getElementById('proxy-input').value = '';
        }
    };

    xhr.onerror = function() {
        showStatusMessage(`Network error during ${fileType} upload. Please check server connection.`, 'error');
        console.error(`Network error during ${fileType} upload.`);
        // Clear textarea if network error
        if (fileType === 'combo') document.getElementById('combo-input').value = '';
        if (fileType === 'proxy') document.getElementById('proxy-input').value = '';
    };

    xhr.send(formData);
    showStatusMessage(`Uploading ${fileType} file...`, 'info');
}

// Function to handle content pasted into textarea (for smaller content via WebSocket)
function uploadContentViaWebSocket(content, fileType) {
    if (!validateSession()) return;

    if (fileType === 'combo') {
        socket.emit('upload_combo', {
            session_id: sessionId,
            content: content
        });
    } else if (fileType === 'proxy') {
        socket.emit('upload_proxy', {
            session_id: sessionId,
            content: content,
            proxy_type: document.getElementById('proxy-type-select').value // Pass selected proxy type
        });
    }
    showStatusMessage(`Processing pasted ${fileType} content...`, 'info');
}


// Event listeners for buttons
document.addEventListener('DOMContentLoaded', function() {

    // Helper function to trigger file input
    function triggerFileInput(fileType) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                uploadFileViaHttp(file, fileType); // Use the new HTTP upload function
            }
        };
        input.click();
    }

    // Upload combo button
    document.getElementById('upload-combo-button').addEventListener('click', () => {
        if (!validateSession()) return;

        const comboContent = document.getElementById('combo-input').value.trim();

        if (comboContent) {
            // If textarea has content, process it via WebSocket
            const lineCount = comboContent.split('\n').length;
            if (lineCount > PASTE_LINE_LIMIT_COMBO) {
                showStatusMessage(`Pasted combo content is too large (${lineCount} lines). Please use the file upload dialog for files larger than ${PA,STE_LINE_LIMIT_COMBO} lines.`, 'error');
                document.getElementById('combo-input').value = ''; // Clear textarea
                return;
            }
            uploadContentViaWebSocket(comboContent, 'combo');
        } else {
            // If textarea is empty, trigger file input
            triggerFileInput('combo');
        }
    });

    // Upload proxy button
    document.getElementById('upload-proxy-button').addEventListener('click', () => {
        if (!validateSession()) return;

        const proxyContent = document.getElementById('proxy-input').value.trim();
        
        if (proxyContent) {
            // If textarea has content, process it via WebSocket
            const lineCount = proxyContent.split('\n').length;
            if (lineCount > PASTE_LINE_LIMIT_PROXY) {
                showStatusMessage(`Pasted proxy content is too large (${lineCount} lines). Please use the file upload dialog for files larger than ${PASTE_LINE_LIMIT_PROXY} lines.`, 'error');
                document.getElementById('proxy-input').value = ''; // Clear textarea
                return;
            }
            uploadContentViaWebSocket(proxyContent, 'proxy');
        } else {
            // If textarea is empty, trigger file input
            triggerFileInput('proxy');
        }
    });

    // Start checker button
    document.getElementById('start-button').addEventListener('click', () => {
        if (!validateSession()) return;

        const threads = parseInt(document.getElementById('threads-input').value);

        if (isNaN(threads) || threads < 1 || threads > 100) {
            showStatusMessage('Please enter a valid thread count (1-100)!', 'error');
            return;
        }

        socket.emit('start_checker', {
            session_id: sessionId,
            threads: threads
        });
    });

    // Stop checker button
    document.getElementById('stop-button').addEventListener('click', () => {
        if (!validateSession()) return;

        socket.emit('stop_checker', {
            session_id: sessionId
        });
    });

    // Pause checker button
    document.getElementById('pause-button').addEventListener('click', () => {
        if (!validateSession()) return;

        socket.emit('pause_checker', {
            session_id: sessionId
        });
    });

    // Continue checker button
    document.getElementById('continue-button').addEventListener('click', () => {
        if (!validateSession()) return;

        socket.emit('continue_checker', {
            session_id: sessionId
        });
    });

    // Download hits button
    document.getElementById('download-hits-button').addEventListener('click', () => {
        if (!validateSession()) return;

        socket.emit('download_hits', {
            session_id: sessionId
        });
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll('.upload-textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 300) + 'px';
        });

        // Add paste event listener
        textarea.addEventListener('paste', function(event) {
            const pastedText = (event.clipboardData || window.clipboardData).getData('text');
            const lineCount = pastedText.split('\n').length;
            const isComboTextarea = this.id === 'combo-input';
            const limit = isComboTextarea ? PASTE_LINE_LIMIT_COMBO : PASTE_LINE_LIMIT_PROXY;

            if (lineCount > limit) {
                event.preventDefault(); // Prevent pasting the content
                showStatusMessage(`Pasted ${isComboTextarea ? 'combo' : 'proxy'} content is too large (${lineCount} lines). Please use the file upload dialog for files larger than ${limit} lines.`, 'error');
                this.value = ''; // Clear any partial paste
            }
        });
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 's':
                    e.preventDefault();
                    document.getElementById('start-button').click();
                    break;
                case 'q':
                    e.preventDefault();
                    document.getElementById('stop-button').click();
                    break;
                case 'p':
                    e.preventDefault();
                    document.getElementById('pause-button').click();
                    break;
                case 'r':
                    e.preventDefault();
                    document.getElementById('continue-button').click();
                    break;
                case 'd':
                    e.preventDefault();
                    document.getElementById('download-hits-button').click();
                    break;
            }
        }
    });

    // Add tooltips for keyboard shortcuts
    document.getElementById('start-button').title = 'Start Checker (Ctrl+S)';
    document.getElementById('stop-button').title = 'Stop Checker (Ctrl+Q)';
    document.getElementById('pause-button').title = 'Pause Checker (Ctrl+P)';
    document.getElementById('continue-button').title = 'Continue Checker (Ctrl+R)';
    document.getElementById('download-hits-button').title = 'Download Hits (Ctrl+D)';

    // No initial button state update needed as they are always enabled
    // updateButtonStates('stopped'); // REMOVED

    // Check for session ID in URL on page load
    const urlParams = new URLSearchParams(window.location.search);
    const urlSessionId = urlParams.get('session');
    if (urlSessionId) {
        localStorage.setItem('sessionId', urlSessionId); // Prioritize URL session ID
    }
});

// Add some visual feedback for button clicks
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn-3d')) {
        // Create ripple effect
        const ripple = document.createElement('span');
        const rect = e.target.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');

        e.target.appendChild(ripple);

        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 600);
    }
});

// Add ripple effect CSS
const style = document.createElement('style');
style.textContent = `
    .btn-3d {
        position: relative;
        overflow: hidden;
    }

    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }

    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
