// Function to fetch history
function fetchHistory(username) {
    fetch(`/fetch-history/${username}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const historyList = document.getElementById('historyList');
                historyList.innerHTML = '';
                data.history.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.className = 'delete';
                    deleteButton.onclick = () => deleteHistoryItem(item, username);
                    li.appendChild(deleteButton);
                    historyList.appendChild(li);
                });
            } else {
                alert('Error fetching history: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to fetch copied text history
function fetchCopiedText(username) {
    fetch(`/fetch-copied-text/${username}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const copiedTextList = document.getElementById('copiedTextList');
                copiedTextList.innerHTML = '';
                data.history.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.className = 'delete';
                    deleteButton.onclick = () => deleteCopiedTextItem(item, username);
                    li.appendChild(deleteButton);
                    copiedTextList.appendChild(li);
                });
            } else {
                alert('Error fetching copied text: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to submit new text
function submitText(username) {
    const text = document.getElementById('textInput').value.trim();
    if (!text) {
        alert('Please enter some text to submit.');
        return;
    }

    fetch(`/update-history/${username}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Text submitted successfully!');
                document.getElementById('textInput').value = '';
                fetchHistory(username); // Refresh the history
            } else {
                alert('Error submitting text: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to delete a history item
function deleteHistoryItem(text, username) {
    fetch(`/delete-history/${username}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('History item deleted!');
                fetchHistory(username); // Refresh the history
            } else {
                alert('Error deleting history item: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to clear history
function clearHistory(username) {
    fetch(`/clear-history/${username}`, {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('History cleared!');
                fetchHistory(username); // Refresh the history
            } else {
                alert('Error clearing history: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to delete a copied text item
function deleteCopiedTextItem(text, username) {
    fetch(`/delete-copied-text/${username}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Copied text item deleted!');
                fetchCopiedText(username); // Refresh the copied text history
            } else {
                alert('Error deleting copied text item: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}

// Function to clear copied text history
function clearCopiedText(username) {
    fetch(`/clear-copied-text/${username}`, {
        method: 'POST',
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Copied text history cleared!');
                fetchCopiedText(username); // Refresh the copied text history
            } else {
                alert('Error clearing copied text: ' + data.message);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
}