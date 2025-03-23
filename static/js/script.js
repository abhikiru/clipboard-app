function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Text copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy text: ", err);
    });
}

// Clipboard Manager: Prompt for text and copy to system clipboard
document.getElementById("clipboard-manager-btn").addEventListener("click", () => {
    const text = prompt("Enter text to copy to clipboard:");
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            alert("Text copied to clipboard!");
        }).catch(err => {
            console.error("Failed to copy text: ", err);
            alert("Failed to copy text.");
        });
    }
});

// Copied Text Viewer: Show the paste area and save pasted text
document.getElementById("copied-text-viewer-btn").addEventListener("click", () => {
    const pasteArea = document.getElementById("paste-text");
    if (pasteArea) {
        pasteArea.focus();
        pasteArea.scrollIntoView({ behavior: "smooth" });
    } else {
        alert("Please go to the dashboard to paste copied text.");
    }
});

// Save Pasted Text to Database
document.getElementById("save-pasted-text")?.addEventListener("click", async () => {
    const userId = document.cookie.split('; ').find(row => row.startsWith('user_id='))?.split('=')[1];
    const text = document.getElementById("paste-text").value;

    if (!userId) {
        alert("Please log in to save pasted text.");
        return;
    }

    if (!text) {
        alert("Please paste some text to save.");
        return;
    }

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
});