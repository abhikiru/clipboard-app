// DOM Elements
const textInput = document.getElementById('text-input');
const actionMode = document.getElementById('action-mode');
const submitBtn = document.getElementById('submit-btn');
const historyList = document.getElementById('history-list'); // For submitted text history
const clearHistoryBtn = document.getElementById('clear-history');
const clipboardManagerSection = document.getElementById('clipboard-manager-section');
const copiedTextSection = document.getElementById('copied-text-section');
const copiedTextList = document.getElementById('copied-text-list');
const clearCopiedTextBtn = document.getElementById('clear-copied-text');
const clipboardManagerBtn = document.getElementById('clipboard-manager-btn');
const copiedTextBtn = document.getElementById('copied-text-btn');
const errorMessage = document.createElement('p');
errorMessage.className = 'error';
clipboardManagerSection.appendChild(errorMessage);

const username = document.querySelector('header p').textContent.split(': ')[1];
let pollingInterval = null; // For polling the copied text history

// Toggle Sections
function showClipboardManager() {
    clipboardManagerSection.style.display = 'block';
    copiedTextSection.style.display = 'none';
    clipboardManagerBtn.classList.add('active');
    copiedTextBtn.classList.remove('active');
    loadSubmittedTextHistory(); // Load submitted text history when tab is opened
    // Stop polling when leaving the Copied Text Viewer
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function showCopiedText() {
    clipboardManagerSection.style.display = 'none';
    copiedTextSection.style.display = 'block';
    clipboardManagerBtn.classList.remove('active');
    copiedTextBtn.classList.add('active');
    loadCopiedText(); // Load copied text when tab is opened
    // Start polling to refresh the copied text history every 2 seconds
    if (!pollingInterval) {
        pollingInterval = setInterval(loadCopiedText, 2000);
    }
}

clipboardManagerBtn.addEventListener('click', showClipboardManager);
copiedTextBtn.addEventListener('click', showCopiedText);

// Load submitted text history (Clipboard Manager)
async function loadSubmittedTextHistory() {
    try {
        const response = await fetch(`/api/submitted_text_history/${username}`, {
            credentials: 'include',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            historyList.innerHTML = '';
            const submittedHistory = data.submitted_text_history || [];
            if (submittedHistory.length === 0) {
                const emptyItem = document.createElement('li');
                emptyItem.textContent = 'No submitted text yet...';
                emptyItem.className = 'text-gray-500';
                historyList.appendChild(emptyItem);
            } else {
                submittedHistory.forEach(item => addToSubmittedTextHistory(item));
            }
        } else {
            throw new Error(data.message || 'Failed to load submitted text history');
        }
    } catch (error) {
        console.error('Error loading submitted text history:', error);
        errorMessage.textContent = `Error loading submitted text history: ${error.message}`;
    }
}

// Load copied text history (Text Viewer)
async function loadCopiedText() {
    try {
        const response = await fetch(`/api/copied_text_history/${username}`, {
            credentials: 'include',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === 'success') {
            copiedTextList.innerHTML = ''; // Clear existing items
            const copiedTextHistory = data.copied_text_history || [];
            if (copiedTextHistory.length === 0) {
                const emptyItem = document.createElement('li');
                emptyItem.textContent = 'No copied text yet...';
                emptyItem.className = 'text-gray-500';
                copiedTextList.appendChild(emptyItem);
            } else {
                // Ensure latest text is at the top
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

// Add to Submitted Text History (Clipboard Manager)
function addToSubmittedTextHistory(text) {
    const existingItems = historyList.getElementsByTagName('li');
    for (let item of existingItems) {
        if (item.querySelector('span') && item.querySelector('span').textContent === text) {
            return;
        }
    }

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
            const response = await fetch(`/api/delete_submitted_text/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ text }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error deleting submitted text item:', error);
            errorMessage.textContent = `Error deleting submitted text item: ${error.message}`;
        }
    });
    listItem.appendChild(deleteBtn);

    const emptyItem = historyList.querySelector('.text-gray-500');
    if (emptyItem) {
        emptyItem.remove();
    }

    historyList.insertBefore(listItem, historyList.firstChild); // Add to top (LIFO)
}

// Add to Copied Text History (Text Viewer)
function addToCopiedText(text) {
    const existingItems = copiedTextList.getElementsByTagName('li');
    for (let item of existingItems) {
        if (item.querySelector('span') && item.querySelector('span').textContent === text) {
            return;
        }
    }

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
                credentials: 'include',
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

    const emptyItem = copiedTextList.querySelector('.text-gray-500');
    if (emptyItem) {
        emptyItem.remove();
    }

    copiedTextList.insertBefore(listItem, copiedTextList.firstChild); // Add to top (LIFO)
}

// Clear Submitted Text History (Clipboard Manager)
clearHistoryBtn.addEventListener('click', async () => {
    historyList.innerHTML = '';
    try {
        const response = await fetch(`/api/clear_submitted_text/${username}`, {
            method: 'POST',
            credentials: 'include',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to clear submitted text history');
        }
    } catch (error) {
        console.error('Error clearing submitted text history:', error);
        errorMessage.textContent = `Error clearing submitted text history: ${error.message}`;
    }
});

// Clear Copied Text History (Text Viewer)
clearCopiedTextBtn.addEventListener('click', async () => {
    copiedTextList.innerHTML = '';
    try {
        const response = await fetch(`/api/clear_copied_text/${username}`, {
            method: 'POST',
            credentials: 'include',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to clear copied text history');
        }
    } catch (error) {
        console.error('Error clearing copied text history:', error);
        errorMessage.textContent = `Error clearing copied text history: ${error.message}`;
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

    errorMessage.textContent = '';

    try {
        // Send text to clipboard_manager.py to copy to system clipboard
        if (mode === 'copy-to-clipboard' || mode === 'both') {
            const clipboardResponse = await fetch(`/api/submit_to_clipboard/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ text }),
            });
            if (!clipboardResponse.ok) {
                throw new Error(`HTTP error! Status: ${clipboardResponse.status}`);
            }
            const clipboardData = await clipboardResponse.json();
            if (clipboardData.status !== 'success') {
                throw new Error(clipboardData.message || 'Failed to send to clipboard');
            }
            alert('Text sent to system clipboard!');
        }

        // Save to submitted_text_history (to show in Clipboard Manager history)
        if (mode === 'add-to-history' || mode === 'both') {
            const historyResponse = await fetch(`/api/submit_submitted_text/${username}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ text }),
            });
            if (!historyResponse.ok) {
                throw new Error(`HTTP error! Status: ${historyResponse.status}`);
            }
            const historyData = await historyResponse.json();
            if (historyData.status !== 'success') {
                throw new Error(historyData.message || 'Failed to add to submitted text history');
            }
            addToSubmittedTextHistory(text); // Add to UI immediately
        }

        textInput.value = ''; // Clear input after submission
    } catch (error) {
        console.error('Error submitting text:', error);
        errorMessage.textContent = `Error submitting text: ${error.message}`;
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    showClipboardManager();
});