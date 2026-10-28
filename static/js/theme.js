// Runs before the page paints so the chosen theme never flashes. Keep it tiny.
(function () {
    var saved = null;
    try { saved = localStorage.getItem('srps-theme'); } catch (e) { /* storage blocked: follow the system */ }
    var dark = saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-bs-theme', dark ? 'dark' : 'light');
})();
