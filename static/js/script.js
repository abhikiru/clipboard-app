document.getElementById('clipboard-manager-btn').addEventListener('click', () => {
    document.getElementById('clipboard-manager').style.display = 'block';
    document.getElementById('copied-text-viewer').style.display = 'none';
});

document.getElementById('copied-text-viewer-btn').addEventListener('click', () => {
    document.getElementById('clipboard-manager').style.display = 'none';
    document.getElementById('copied-text-viewer').style.display = 'block';
});

document.getElementById('copy-btn').addEventListener('click', () => {
    const text = document.getElementById('clipboard-text').value;
    navigator.clipboard.writeText(text).then(() => {
        alert('Text copied to clipboard');
    });
});

document.getElementById('save-btn').addEventListener('click', () => {
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
    });
});