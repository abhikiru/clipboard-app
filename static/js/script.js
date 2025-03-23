// DOM Elements
const loginSection = document.getElementById('login-section');
const mainContent = document.getElementById('main-content');
const usernameInput = document.getElementById('username-input');
const passwordInput = document.getElementById('password-input');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');
const loggedInUser = document.getElementById('logged-in-user');
const copiedTextList = document.getElementById('copied-text-list');

let currentUserId = null;
let pollingInterval = null;

// Login Logic
loginBtn.addEventListener('click', () => {
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        loginError.textContent = 'Please enter both username and password.';
        return;
    }

    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                currentUserId = data.user_id;
                loginSection.style.display = 'none';
                mainContent.style.display = 'block';
                loggedInUser.textContent = username;
                loadCopiedText();
                pollingInterval = setInterval(loadCopiedText, 2000);
            } else {
                loginError.textContent = 'Invalid credentials. Please try again.';
            }
        })
        .catch(error => {
            console.error('Error during login:', error);
            loginError.textContent = 'Failed to connect to server. Please try again.';
        });
});

// Load copied text history
function loadCopiedText() {
    fetch(`/fetch-copied-text/${currentUserId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Copied text history loaded:', data.history);
                copiedTextList.innerHTML = '';
                if (data.history.length === 0) {
                    const emptyItem = document.createElement('li');
                    emptyItem.textContent = 'No copied text yet...';
                    copiedTextList.appendChild(emptyItem);
                } else {
                    data.history.forEach(item => {
                        const listItem = document.createElement('li');
                        listItem.textContent = item;
                        copiedTextList.appendChild(listItem);
                    });
                }
            } else {
                console.error('Failed to load copied text history:', data.message);
            }
        })
        .catch(error => console.error('Error loading copied text history:', error));
}