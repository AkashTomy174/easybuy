function toggleSubList(categoryId) {
    const subList = document.getElementById(`sub-${categoryId}`);
    const btn = event.currentTarget; // Captures the button clicked

    if (subList) {
        const isHidden = subList.classList.contains('hidden');
        
        // Toggle visibility
        subList.classList.toggle('hidden');
        
        // Optional: Update button text for better UX
        if (!isHidden) {
            btn.innerText = `+${subList.dataset.count} more`;
        } else {
            btn.innerText = `show less`;
        }
    }
}