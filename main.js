document.getElementById('poem-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        title: e.target.title.value,
        poet: e.target.poet.value,
        poem: e.target.poem.value,
        style: e.target.style.value
    };

    try {
        const response = await fetch('http://127.0.0.1:5000/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'حدث خطأ غير متوقع');
        }

        // عرض النتيجة
        const imgElement = document.getElementById('poem-image');
        imgElement.src = data.image_url + '?t=' + new Date().getTime();
        imgElement.style.display = 'block';
        
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.href = data.image_url;
        downloadBtn.download = `قصيدة-${formData.title}.webp`;
        
        document.getElementById('design-suggestion').textContent = data.design_suggestion;
        document.getElementById('result').classList.remove('hidden');
        
    } catch (error) {
        console.error('Error:', error);
        alert(`فشل إنشاء التصميم: ${error.message}`);
    }
});