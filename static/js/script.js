// DOM Elements
const textInput = document.getElementById('text-input');
const actionMode = document.getElementById('action-mode');
const submitBtn = document.getElementById('submit-btn');
const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history');
const clipboardManagerSection = document.getElementById('clipboard-manager-section');
const copiedTextSection = document.getElementById('copied-text-section');
const copiedTextList = document.getElementById('copied-text-list');
const clearCopiedTextBtn = document.getElementById('clear-copied-text');
const clipboardManagerBtn = document.getElementById('clipboard-manager-btn');
const copiedTextBtn = document.getElementById('copied-text-btn');
const errorMessage = document.createElement('p'); // Add an error message element
errorMessage.className = 'error';
clipboardManagerSection.appendChild(errorMessage);

const username = document.querySelector('header p').textContent.split(': ')[1];
let ws = null;

// WebSocket Connection
function connectWebSocket() {
    ws = new WebSocket(`wss://clipboard-app-seven.vercel.app/ws/${username}`);
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        if (data.type === 'history_update') {
            addToHistory(data.text);
        } else if (data.type === 'copied_text_update') {
            addToCopiedText(data.text);
        } else if (data.type === 'history_delete') {
            const items = historyList.getElementsByTagName('li');
            for (let item of items) {
                if (item.querySelector('span').textContent === data.text) {
                    item.remove();
                    break;
                }
            }
        } else if (data.type === 'copied_text_delete') {
            const items = copiedTextList.getElementsByTagName('li');
            for (let item of items) {
                if (item.querySelector('span').textContent === data.text) {
                    item.remove();
                    break;
                }
            }
        } else if (data.type === 'history_clear') {
            historyList.innerHTML = '';
        } else if (data.type === 'copied_text_clear') {
            copiedTextList.innerHTML = '';
        }
    };
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
    };
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        errorMessage.textContent = 'WebSocket error occurred. Please try again.';
    };
}

// Toggle Sections
function showClipboardManager() {
    clipboardManagerSection.style.display = 'block';
    copiedTextSection.style.display = 'none';
    clipboardManagerBtn.classList.add('active');
    copiedTextBtn.classList.remove('active');
}

function showCopiedText() {
    clipboardManagerSection.style.display = 'none';
    copiedTextSection.style.display = 'block';
    clipboardManagerBtn.classList.remove('active');
    copiedTextBtn.classList.add('active');
    loadCopiedText(); // Load copied text once when the tab is opened
}

clipboardManagerBtn.addEventListener('click', showClipboardManager);
copiedTextBtn.addEventListener('click', showCopiedText);

// Load history (Clipboard Manager)
async function loadHistory() {
    try {
        const response = await fetch(`/api/history/${username}`);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            historyList.innerHTML = '';
            const history = data.history || [];
            history.forEach(item => addToHistory(item));
        } else {
            throw new Error(data.message || 'Failed to load history');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        errorMessage.textContent = `Error loading history: ${error.message}`;
    }
}

// Load copied text history
async function loadCopiedText() {
    try {
        const response = await fetch(`/api/history/${username}`);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            copiedTextList.innerHTML = '';
            const copiedTextHistory = data.copied_text_history || [];
            if (copiedTextHistory.length === 0) {
                const emptyItem = document.createElement('li');
                emptyItem.textContent = 'No copied text yet...';
                emptyItem.className = 'text-gray-500';
                copiedTextList.appendChild(emptyItem);
            } else {
                copiedTextHistory.forEach(item => addToCopiedText(item));
            }
        } else {
            throw new Error(data.message || 'Failed to load copied text');
        }
    } catch (error) {
        console.error('Error loading copied text history:', error);
        errorMessage.textContent = `Error loading copied text: ${error.message}`;
    }
}

// Add to Clipboard Manager History
function addToHistory(text) {
    const listItem = document.createElement('li');
    listItem.className = 'history-item';

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    listItem.appendChild(textSpan);

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'copy-btn';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(text).then(() => {
            alert('Text copied to clipboard!');
        });
    });
    listItem.appendChild(copyBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '✕';
    deleteBtn.className = 'delete-btn';
    deleteBtn.addEventListener('click', async () => {
        listItem.remove();
        try {
            const response = await fetch(`/api/delete_history/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error deleting history item:', error);
            errorMessage.textContent = `Error deleting history item: ${error.message}`;
        }
    });
    listItem.appendChild(deleteBtn);

    historyList.insertBefore(listItem, historyList.firstChild);
}

// Add to Copied Text History
function addToCopiedText(text) {
    const listItem = document.createElement('li');
    listItem.className = 'history-item';

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    listItem.appendChild(textSpan);

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'copy-btn';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(text).then(() => {
            alert('Text copied to clipboard!');
        });
    });
    listItem.appendChild(copyBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '✕';
    deleteBtn.className = 'delete-btn';
    deleteBtn.addEventListener('click', async () => {
        listItem.remove();
        try {
            const response = await fetch(`/api/delete_copied_text/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error deleting copied text item:', error);
            errorMessage.textContent = `Error deleting copied text item: ${error.message}`;
        }
    });
    listItem.appendChild(deleteBtn);

    // Remove "No copied text yet..." message if it exists
    const emptyItem = copiedTextList.querySelector('.text-gray-500');
    if (emptyItem) {
        emptyItem.remove();
    }

    copiedTextList.insertBefore(listItem, copiedTextList.firstChild);
}

// Clear History (Clipboard Manager)
clearHistoryBtn.addEventListener('click', async () => {
    historyList.innerHTML = '';
    try {
        const response = await fetch(`/api/clear_history/${username}`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        errorMessage.textContent = `Error clearing history: ${error.message}`;
    }
});

// Clear Copied Text History
clearCopiedTextBtn.addEventListener('click', async () => {
    copiedTextList.innerHTML = '';
    try {
        const response = await fetch(`/api/clear_copied_text/${username}`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error clearing copied text:', error);
        errorMessage.textContent = `Error clearing copied text: ${error.message}`;
    }
});

// Submit Button Logic (Clipboard Manager)
submitBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    const mode = actionMode.value;

    if (!text) {
        alert('Please enter some text!');
        return;
    }

    errorMessage.textContent = ''; // Clear previous errors

    try {
        if (mode === 'copy' || mode === 'both') {
            const response = await fetch(`/api/submit_copied_text/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error(data.message || 'Failed to add to copied text history');
            }
            alert('Text added to copied text history!');
        }

        if (mode === 'history' || mode === 'both') {
            const response = await fetch(`/api/submit/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            if (data.status !== 'success') {
                throw new Error(data.message || 'Failed to add to history');
            }
        }

        textInput.value = '';
    } catch (error) {
        console.error('Error submitting text:', error);
        errorMessage.textContent = `Error submitting text: ${error.message}`;
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    showClipboardManager();
    loadHistory();
    connectWebSocket();
});