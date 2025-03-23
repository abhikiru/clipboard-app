function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Text copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy text: ", err);
    });
}

// Clipboard Manager functionality
document.getElementById("clipboard-manager-btn").addEventListener("click", async () => {
    const userId = document.cookie.split('; ').find(row => row.startsWith('user_id='))?.split('=')[1];
    if (!userId) {
        alert("Please log in to use the Clipboard Manager.");
        return;
    }

    const text = prompt("Enter text to save to clipboard:");
    if (text) {
        try {
            const response = await fetch("/api/save_text", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ user_id: parseInt(userId), text: text }),
            });
            const result = await response.json();
            alert(result.message);
            window.location.reload(); // Refresh to show the new text
        } catch (err) {
            console.error("Failed to save text: ", err);
            alert("Failed to save text.");
        }
    }
});

// Copied Text Viewer functionality
document.getElementById("copied-text-viewer-btn").addEventListener("click", () => {
    const table = document.getElementById("copied-text-table");
    if (table) {
        table.classList.toggle("hidden");
    } else {
        alert("Please go to the dashboard to view copied texts.");
    }
});