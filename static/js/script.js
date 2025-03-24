document.addEventListener("DOMContentLoaded", () => {
    // Elements for Clipboard Manager
    const clipboardTextArea = document.getElementById("clipboard-text");
    const copyToClipboardBtn = document.getElementById("copy-to-clipboard-btn");

    // Elements for Copied Text Viewer
    const pastedTextArea = document.getElementById("pasted-text");
    const savePastedTextBtn = document.getElementById("save-pasted-text-btn");

    // Footer buttons
    const clipboardManagerBtn = document.getElementById("clipboard-manager-btn");
    const copiedTextViewerBtn = document.getElementById("copied-text-viewer-btn");

    // Sections to toggle
    const clipboardManagerSection = document.querySelector(".bg-white:has(#clipboard-text)");
    const copiedTextViewerSection = document.querySelector(".bg-white:has(#pasted-text)");

    // Check if we're on the user dashboard (by checking if clipboardTextArea exists)
    if (clipboardTextArea && copyToClipboardBtn) {
        // Copy to Clipboard functionality
        copyToClipboardBtn.addEventListener("click", () => {
            const text = clipboardTextArea.value.trim();
            if (text) {
                navigator.clipboard.writeText(text)
                    .then(() => {
                        alert("Text copied to clipboard!");
                        clipboardTextArea.value = ""; // Clear the textarea
                    })
                    .catch(err => {
                        console.error("Failed to copy text: ", err);
                        alert("Failed to copy text to clipboard.");
                    });
            } else {
                alert("Please enter some text to copy.");
            }
        });
    }

    // Save Pasted Text functionality
    if (pastedTextArea && savePastedTextBtn) {
        savePastedTextBtn.addEventListener("click", () => {
            const text = pastedTextArea.value.trim();
            const userId = savePastedTextBtn.getAttribute("data-user-id");

            if (text && userId) {
                fetch("/api/save_text", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ user_id: parseInt(userId), text: text }),
                })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        pastedTextArea.value = ""; // Clear the textarea
                        location.reload(); // Reload the page to update the copied text history
                    })
                    .catch(err => {
                        console.error("Failed to save text: ", err);
                        alert("Failed to save the pasted text.");
                    });
            } else {
                alert("Please paste some text to save.");
            }
        });
    }

    // Toggle visibility of sections using footer buttons (only on user dashboard)
    if (clipboardManagerBtn && copiedTextViewerBtn && clipboardManagerSection && copiedTextViewerSection) {
        // Initially hide both sections
        clipboardManagerSection.style.display = "none";
        copiedTextViewerSection.style.display = "none";

        // Show Clipboard Manager section
        clipboardManagerBtn.addEventListener("click", () => {
            clipboardManagerSection.style.display = "block";
            copiedTextViewerSection.style.display = "none";
        });

        // Show Copied Text Viewer section
        copiedTextViewerBtn.addEventListener("click", () => {
            clipboardManagerSection.style.display = "none";
            copiedTextViewerSection.style.display = "block";
        });
    }
});