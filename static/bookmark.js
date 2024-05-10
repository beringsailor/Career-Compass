function toggleBookmark(userId, jobCode) {
    var bookmarkIcon = document.getElementById('bookmarkIcon-' + jobCode);
    // Send AJAX request to Flask API
    fetch('/bookmark/' + userId + '/' + jobCode)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Update icon and text based on response
            if (data.action === 'add') {
                bookmarkIcon.src = "{{ url_for('static', filename='star_filled.png') }}";
                // bookmarkIcon.parentNode.querySelector('p').textContent = '已收藏';
            } else {
                bookmarkIcon.src = "{{ url_for('static', filename='star_empty.png') }}";
                // bookmarkIcon.parentNode.querySelector('p').textContent = '未收藏';
            }
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
}