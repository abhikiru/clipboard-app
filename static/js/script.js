// DOM Elements
const textInput = document.getElementById('text-input');
const actionMode = document.getElementById('action-mode');
const submitBtn = document.getElementById('submit-btn');
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
    loadCopiedText();
}

clipboardManagerBtn.addEventListener('click', showClipboardManager);
copiedTextBtn.addEventListener('click', showCopiedText);

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

    copiedTextList.insertBefore(listItem, copiedTextList.firstChild);
}

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

    errorMessage.textContent = '';

    try {
        if (mode === 'copy-to-clipboard' || mode === 'both') {
            // Send text to clipboard_manager.py to copy to system clipboard
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
        }

        if (mode === 'add-to-history' || mode === 'both') {
            // Save to copied_text_history (to show in Text Viewer)
            const historyResponse = await fetch(`/api/submit_copied_text/${username}`, {
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
                throw new Error(historyData.message || 'Failed to add to history');
            }
        }

        alert('Text processed successfully!');
        textInput.value = '';
    } catch (error) {
        console.error('Error submitting text:', error);
        errorMessage.textContent = `Error submitting text: ${error.message}`;
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    showClipboardManager();
});