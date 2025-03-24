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

let pollingInterval = null;
const username = document.querySelector('header p').textContent.split(': ')[1];

// Toggle Sections
function showClipboardManager() {
    clipboardManagerSection.classList.remove('hidden');
    copiedTextSection.classList.add('hidden');
    clipboardManagerBtn.classList.add('active', 'bg-blue-800');
    copiedTextBtn.classList.remove('active', 'bg-blue-800');
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function showCopiedText() {
    clipboardManagerSection.classList.add('hidden');
    copiedTextSection.classList.remove('hidden');
    clipboardManagerBtn.classList.remove('active', 'bg-blue-800');
    copiedTextBtn.classList.add('active', 'bg-blue-800');
    loadCopiedText();
    if (!pollingInterval) {
        pollingInterval = setInterval(loadCopiedText, 2000);
    }
}

clipboardManagerBtn.addEventListener('click', showClipboardManager);
copiedTextBtn.addEventListener('click', showCopiedText);

// Load history (Clipboard Manager)
async function loadHistory() {
    try {
        const response = await fetch(`/fetch-history/${username}`);
        const data = await response.json();
        if (data.status === 'success') {
            historyList.innerHTML = '';
            data.history.forEach(item => addToHistory(item));
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Load copied text history
async function loadCopiedText() {
    try {
        const response = await fetch(`/fetch-copied-text/${username}`);
        const data = await response.json();
        if (data.status === 'success') {
            copiedTextList.innerHTML = '';
            if (data.history.length === 0) {
                const emptyItem = document.createElement('li');
                emptyItem.textContent = 'No copied text yet...';
                emptyItem.className = 'text-gray-500';
                copiedTextList.appendChild(emptyItem);
            } else {
                data.history.forEach(item => addToCopiedText(item));
            }
        }
    } catch (error) {
        console.error('Error loading copied text history:', error);
    }
}

// Add to Clipboard Manager History
function addToHistory(text) {
    const listItem = document.createElement('li');
    listItem.className = 'flex items-center justify-between bg-gradient-to-r from-white to-gray-100 p-4 rounded-lg shadow-md h-20 overflow-hidden animate-fade-in';

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    textSpan.className = 'flex-1 font-medium break-all overflow-y-auto max-h-full pr-4 text-gray-800';
    listItem.appendChild(textSpan);

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 mr-2';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(text).then(() => {
            alert('Text copied to clipboard!');
        });
    });
    listItem.appendChild(copyBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '✕';
    deleteBtn.className = 'py-2 px-4 bg-red-500 text-white rounded-lg hover:bg-red-600';
    deleteBtn.addEventListener('click', async () => {
        listItem.remove();
        await fetch(`/delete-history/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
    });
    listItem.appendChild(deleteBtn);

    historyList.insertBefore(listItem, historyList.firstChild);
}

// Add to Copied Text History
function addToCopiedText(text) {
    const listItem = document.createElement('li');
    listItem.className = 'flex items-center justify-between bg-gradient-to-r from-white to-gray-100 p-4 rounded-lg shadow-md h-20 overflow-hidden animate-fade-in';

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    textSpan.className = 'flex-1 font-medium break-all overflow-y-auto max-h-full pr-4 text-gray-800';
    listItem.appendChild(textSpan);

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 mr-2';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(text).then(() => {
            alert('Text copied to clipboard!');
        });
    });
    listItem.appendChild(copyBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '✕';
    deleteBtn.className = 'py-2 px-4 bg-red-500 text-white rounded-lg hover:bg-red-600';
    deleteBtn.addEventListener('click', async () => {
        listItem.remove();
        await fetch(`/delete-copied-text/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
    });
    listItem.appendChild(deleteBtn);

    copiedTextList.insertBefore(listItem, copiedTextList.firstChild);
}

// Clear History (Clipboard Manager)
clearHistoryBtn.addEventListener('click', async () => {
    historyList.innerHTML = '';
    await fetch(`/clear-history/${username}`, { method: 'POST' });
});

// Clear Copied Text History
clearCopiedTextBtn.addEventListener('click', async () => {
    copiedTextList.innerHTML = '';
    await fetch(`/clear-copied-text/${username}`, { method: 'POST' });
});

// Submit Button Logic (Clipboard Manager)
submitBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    const mode = actionMode.value;

    if (!text) {
        alert('Please enter some text!');
        return;
    }

    if (mode === 'copy' || mode === 'both') {
        await fetch(`/update-copied-text/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        alert('Text added to copied text history!');
    }

    if (mode === 'history' || mode === 'both') {
        addToHistory(text);
        await fetch(`/update-history/${username}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
    }

    textInput.value = '';
});

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    showClipboardManager();
    loadHistory();
});