(() => {
    const toggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.getElementById("main-sidebar");

    if (!toggle || !sidebar) return;

    const closeMenu = () => {
        sidebar.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Abrir menu principal");
    };

    toggle.addEventListener("click", () => {
        const open = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Fechar menu principal" : "Abrir menu principal");
    });

    sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
    window.addEventListener("resize", () => {
        if (window.innerWidth > 760) closeMenu();
    });
})();
