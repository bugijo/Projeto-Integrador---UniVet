(() => {
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const button = form.querySelector("[data-confirm]");
            if (button && !window.confirm(button.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
})();
