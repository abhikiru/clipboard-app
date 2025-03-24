document.addEventListener('DOMContentLoaded', () => {
    const clipboardManager = document.getElementById('clipboard-manager');
    const copiedTextViewer = document.getElementById('copied-text-viewer');
    const clipboardManagerBtn = document.getElementById('clipboard-manager-btn');
    const copiedTextViewerBtn = document.getElementById('copied-text-viewer-btn');

    if (clipboardManagerBtn && copiedTextViewerBtn) {
        clipboardManagerBtn.addEventListener('click', () => {
            clipboardManager.style.display = 'block';
            copiedTextViewer.style.display = 'none';
        });

        copiedTextViewerBtn.addEventListener('click', () => {
            clipboardManager.style.display = 'none';
            copiedTextViewer.style.display = 'block';
        });
    }

    const copyBtn = document.getElementById('copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const text = document.getElementById('clipboard-text').value;
            navigator.clipboard.writeText(text).then(() => {
                alert('Text copied to clipboard');
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                alert('Failed to copy text. Please copy manually.');
            });
        });
    }

    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const text = document.getElementById('pasted-text').value;
            fetch('/api/save_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `text=${encodeURIComponent(text)}`
            }).then(response => {
                if (response.ok) {
                    alert('Text saved');
                    location.reload();
                } else {
                    alert('Failed to save text');
                }
            }).catch(err => {
                console.error('Failed to save text: ', err);
                alert('Failed to save text');
            });
        });
    }

    // Handle Ctrl+C for Copied Text Viewer
    document.addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.key === 'c' && copiedTextViewer.style.display === 'block') {
            navigator.clipboard.readText().then(text => {
                document.getElementById('pasted-text').value = text;
            }).catch(err => {
                console.error('Failed to read clipboard: ', err);
                alert('Failed to read clipboard. Please paste manually.');
            });
        }
    });
});