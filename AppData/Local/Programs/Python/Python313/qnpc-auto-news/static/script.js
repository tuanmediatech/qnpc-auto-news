document.addEventListener('DOMContentLoaded', function () {
    const fetchForm = document.getElementById('fetchForm');
    const numInput = document.getElementById('num_articles');
    const fetchBtn = document.getElementById('fetchBtn');
    const logBox = document.getElementById('logBox');

    fetchForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const num_articles = numInput.value;
        if (!num_articles || num_articles <= 0) return;

        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '⏳ Đang xử lý...';
        logBox.innerHTML = '';

        const formData = new FormData();
        formData.append('num_articles', num_articles);

        fetch('/stream_logs', {
            method: 'POST',
            body: formData
        }).then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');

            function readStream() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        fetchBtn.disabled = false;
                        fetchBtn.innerHTML = '🚀 Bắt đầu lấy bài viết';
                        return;
                    }

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    lines.forEach(line => {
                        if (line.startsWith('data: ')) {
                            const message = line.replace('data: ', '');
                            logBox.innerHTML += message + '\n';
                            logBox.scrollTop = logBox.scrollHeight;
                        }
                    });

                    readStream(); // tiếp tục đọc
                });
            }

            readStream();
        }).catch(error => {
            logBox.innerHTML += `❌ Lỗi khi gửi yêu cầu: ${error}\n`;
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = '🚀 Bắt đầu lấy bài viết';
        });
    });
});
