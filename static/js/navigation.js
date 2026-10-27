(() => {
    document.querySelectorAll('form:has(input[name="operacao_token"])').forEach((form) => {
        form.addEventListener('submit', () => {
            form.querySelectorAll('button[type="submit"]').forEach((button) => { button.disabled = true; });
        });
    });
    window.addEventListener('pageshow', () => {
        document.querySelectorAll('form:has(input[name="operacao_token"]) button[type="submit"]').forEach((button) => { button.disabled = false; });
    });
    const toggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.getElementById("main-sidebar");

    if (!toggle || !sidebar) return;

    const closeMenu = () => {
        sidebar.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Abrir menu principal");
    };

    toggle.addEventListener("click", () => {
        const topbar = document.querySelector('.topbar');
        if (topbar) sidebar.style.setProperty('--topbar-height', `${topbar.getBoundingClientRect().bottom}px`);
        const open = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Fechar menu principal" : "Abrir menu principal");
    });

    sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && sidebar.classList.contains('is-open')) { closeMenu(); toggle.focus(); }
    });
    document.addEventListener('click', (event) => {
        if (!sidebar.contains(event.target) && !toggle.contains(event.target)) closeMenu();
    });
    window.addEventListener("resize", () => {
        closeMenu();
    });
})();
