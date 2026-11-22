// Visitors do not contact the editor API or load the editor UI.
(() => {
  const script = document.currentScript;
  function load() {
    try {
      if (location.hash !== '#edit' && !location.hash.startsWith('#owner=') &&
          !sessionStorage.getItem('portfolio.owner.session') && !sessionStorage.getItem('portfolio.owner.login')) return;
      import(new URL('owner.mjs', script.src)).then(m => m.start(script.dataset.api)).catch(err => {
        console.error(err); alert('편집기를 열지 못했습니다. 페이지를 다시 열어 주세요.');
      });
    } catch (_) { /* A visitor with storage disabled still gets the static page. */ }
  }
  load(); window.addEventListener('hashchange', load);
})();
