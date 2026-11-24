// The document already contains every gallery, image and detail link.
(() => {
  'use strict';
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');

  const projects = document.getElementById('projects');
  const stats = Array.from(document.querySelectorAll('.highlights button[data-filter]'));
  if (projects && stats.length) {
    const status = document.getElementById('works-filter-status');
    const all = stats.find(stat => stat.dataset.filter === 'projects');
    let active = null;

    function applyFilter(button) {
      active = button;
      const filter = button?.dataset.filter;
      let total = 0;
      for (const shelf of projects.querySelectorAll('.shelf')) {
        let count = 0;
        for (const work of shelf.querySelectorAll('.work')) {
          work.hidden = (filter === 'awards' && work.dataset.award !== '1') ||
                        (filter === 'ai' && work.dataset.ai !== '1');
          if (!work.hidden) count++;
        }
        // When unfiltered, let the shelf's is-empty class expose empty editor drop targets.
        shelf.hidden = !!button && count === 0;
        total += count;
      }
      for (const stat of stats) stat.setAttribute('aria-pressed', String(stat === button));
      const label = (button ?? all)?.querySelector('[data-edit-field="label"]').textContent ?? '전체';
      status.textContent = `${label} ${total}`;
    }

    for (const stat of stats) stat.addEventListener('click', e => {
      if (e.defaultPrevented || (document.body.classList.contains('owner-editing') && e.target.closest('[data-edit-group]'))) return;
      applyFilter(stat === active || stat.dataset.filter === 'projects' ? null : stat);
      projects.scrollIntoView({block:'start', behavior:motion.matches ? 'instant' : 'smooth'});
    });
    document.addEventListener('works-filter-reset', () => { if (active) applyFilter(null); });
  }

  function setupGallery(gallery) {
    // Keep the player out of the initial document, even in a single-video gallery.
    const link = gallery.querySelector('[data-youtube]');
    let facade;
    if (link) {
      const {youtube, title} = link.dataset;
      facade = document.createElement('button');
      facade.type = 'button';
      facade.className = link.className;
      facade.setAttribute('aria-label', link.getAttribute('aria-label'));
      facade.append(...link.childNodes);
      link.replaceWith(facade);
      facade.addEventListener('click', () => {
        const frame = document.createElement('iframe');
        frame.title = title;
        frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
        frame.allowFullscreen = true;
        frame.src = `https://www.youtube-nocookie.com/embed/${youtube}?autoplay=1&rel=0`;
        facade.replaceWith(frame);
        frame.focus();
      });
    }

    const slides = Array.from(gallery.querySelectorAll('.media-slide'));
    if (slides.length < 2) return;
    const stage = gallery.querySelector('.media-stage');
    const strip = gallery.querySelector('.media-thumbs');
    const thumbs = Array.from(strip.children);
    const count = gallery.querySelector('.media-count');
    let index = 0;
    function mark(i, current) {
      slides[i].classList.toggle('is-current', current);
      slides[i].inert = !current;
      if (current) thumbs[i].setAttribute('aria-current', 'true');
      else thumbs[i].removeAttribute('aria-current');
    }
    function select(target) {
      const next = (target + slides.length) % slides.length;
      if (next === index) return;
      const old = slides[index];
      if (old.contains(document.activeElement) || strip.contains(document.activeElement)) {
        thumbs[next].focus({preventScroll:true});
      }
      old.querySelector('video')?.pause();
      old.querySelector('iframe')?.replaceWith(facade);
      mark(index, false);
      index = next;
      mark(index, true);
      count.textContent = `${index + 1} / ${slides.length}`;
      const tile = thumbs[index].getBoundingClientRect(), bounds = strip.getBoundingClientRect();
      strip.scrollLeft += Math.min(0, tile.left - bounds.left) + Math.max(0, tile.right - bounds.right);
    }
    thumbs.forEach((thumb, i) => {
      mark(i, i === index);
      thumb.addEventListener('click', () => select(i));
    });
    gallery.querySelector('[data-prev]').addEventListener('click', () => select(index - 1));
    gallery.querySelector('[data-next]').addEventListener('click', () => select(index + 1));
    gallery.addEventListener('keydown', e => {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      if (e.target.closest('video, iframe')) return;  // Arrow keys seek inside a focused video.
      e.preventDefault();
      select(index + (e.key === 'ArrowLeft' ? -1 : 1));
    });
    let start;
    stage.addEventListener('touchstart', e => {
      start = e.touches.length === 1 && !e.target.closest('.media-arrows') ? e.touches[0] : null;
      // Leave the native video transport bar available for scrubbing.
      if (start && e.target.matches('video') && start.clientY >= e.target.getBoundingClientRect().bottom - 48) start = null;
    }, {passive:true});
    stage.addEventListener('touchcancel', () => { start = null; });
    stage.addEventListener('touchend', e => {
      if (!start) return;
      const end = e.changedTouches[0];
      const dx = end.clientX - start.clientX, dy = end.clientY - start.clientY;
      start = null;
      if (Math.abs(dx) < 45 || Math.abs(dx) < 1.5 * Math.abs(dy)) return;
      if (e.cancelable) e.preventDefault();
      select(index + (dx < 0 ? 1 : -1));
    }, {passive:false});
    gallery.classList.add('gallery-ready');
    gallery.tabIndex = 0;
    gallery.querySelector('.media-arrows').hidden = gallery.querySelector('.media-nav').hidden = false;
  }
  document.querySelectorAll('.media-gallery').forEach(setupGallery);

  const progress = document.querySelector('.progress');
  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      const distance = document.documentElement.scrollHeight - innerHeight;
      progress.style.transform = `scaleX(${distance > 0 ? Math.max(0, Math.min(1, scrollY/distance)) : 0})`;
      scheduled = false;
    });
  }
  window.addEventListener('scroll', schedule, {passive:true});
  window.addEventListener('resize', schedule);
  if ('ResizeObserver' in window) new ResizeObserver(schedule).observe(document.body);
  schedule();
  if ('IntersectionObserver' in window && !motion.matches) {
    const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('arrived'); reveal.unobserve(entry.target);
    }));
    document.querySelectorAll('.tile,.prose').forEach(el => reveal.observe(el));
  }
})();
