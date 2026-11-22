// The document already contains every gallery, image and detail link.
(() => {
  'use strict';
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const moving = new Map();
  function setDisclosure(details, open) {
    const run = moving.get(details);
    if (run) {
      moving.delete(details);
      run.effects.forEach(effect => effect.cancel());
    }
    details.classList.remove('revealing');
    details.open = open;
  }

  document.querySelectorAll('.profile-disclosure, .earlier-activities').forEach(details => {
    const summary = details.querySelector(':scope > summary');
    const body = summary.nextElementSibling;
    const profile = details.matches('.profile-disclosure');
    function continueHistory(hadFocus) {
      // The summary disappears once opened, so carry keyboard focus into the revealed history.
      const first = body.firstElementChild;
      if (!hadFocus || !first) return;
      first.tabIndex = -1;
      first.focus({preventScroll:true});
    }
    function adjustScroll(open) {
      if (open !== profile) return; // Only entering the profile or returning to the activities row.
      const anchor = open ? body : summary;
      const top = anchor.getBoundingClientRect().top;
      if (top < 0 || (open && top >= innerHeight)) {
        anchor.scrollIntoView({block:'start', behavior:motion.matches ? 'instant' : 'smooth'});
      }
    }
    summary.addEventListener('click', e => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey ||
          document.body.classList.contains('owner-editing')) return;
      const hadFocus = document.activeElement === summary;
      if (!profile && (details.open || moving.has(details))) { e.preventDefault(); return; } // One-way reveal.
      if (motion.matches || !body.animate) {
        const open = !details.open;
        requestAnimationFrame(() => {
          if (e.defaultPrevented || details.open !== open) return;
          adjustScroll(open);
          if (!profile) continueHistory(hadFocus);
        });
        return; // Let summary perform its native toggle.
      }
      e.preventDefault();
      const active = moving.get(details);
      if (active) {
        active.open = !active.open;
        active.effects.forEach(effect => effect.reverse());
        return;
      }
      // Settle a nested transition before measuring the new content height.
      for (const [other, run] of moving) {
        if (other.contains(details)) setDisclosure(other, true);
        else if (details.contains(other)) setDisclosure(other, run.open);
      }
      const open = !details.open;
      details.open = true; // Keep the content rendered until a closing animation finishes.
      const timing = {duration:320, easing:'cubic-bezier(.25,.7,.3,1)', fill:'both', direction:open ? 'normal' : 'reverse'};
      const height = body.getBoundingClientRect().height;
      const size = body.animate([
        {height:'0px', opacity:0, overflow:'hidden'},
        {height:`${height}px`, opacity:1, overflow:'hidden'}
      ], timing);
      const items = profile ? body.firstElementChild.children : body.children;
      const effects = [size];
      Array.from(items).forEach((item, i) => {
        const from = {opacity:0, transform:'translateY(5px)'};
        effects.push(item.animate([from, {...from, offset:.05 + Math.min(i, 6) * .06}, {opacity:1, transform:'none'}], timing));
      });
      if (!profile) {
        // The row button folds away while the earlier entries slide in beneath it.
        details.classList.add('revealing');
        effects.push(summary.animate([
          {height:`${summary.getBoundingClientRect().height}px`, opacity:1, overflow:'hidden'},
          {height:'0px', opacity:0, paddingTop:0, paddingBottom:0, overflow:'hidden'}
        ], {...timing, duration:260}));
      }
      const run = {open, effects};
      moving.set(details, run);
      size.onfinish = () => {
        if (moving.get(details) !== run || size.playState !== 'finished') return;
        const finalOpen = run.open && details.open;
        setDisclosure(details, finalOpen);
        adjustScroll(finalOpen);
        if (!profile && finalOpen) continueHistory(hadFocus);
      };
    });
  });
  motion.addEventListener('change', () => {
    if (motion.matches) for (const [details, run] of moving) setDisclosure(details, run.open);
  });

  const profile = document.getElementById('profile');
  if (profile) {
    function profileTarget(hash) {
      const target = document.getElementById(hash.slice(1));
      return profile.contains(target) ? target : null;
    }
    function revealProfile(target) {
      setDisclosure(profile, true);
      const earlier = target.closest('.earlier-activities');
      if (earlier) setDisclosure(earlier, true);
    }
    function fromHash() {
      const target = profileTarget(location.hash);
      if (target) {
        revealProfile(target);
        target.scrollIntoView();
      }
    }
    fromHash();
    window.addEventListener('hashchange', fromHash);
    document.addEventListener('click', e => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = e.target.closest('a[href^="index.html#"], a.tile[href^="#"]');
      const target = link && profileTarget(link.hash);
      if (!target) return;
      // Repeated fragment navigation need not fire hashchange after a manual collapse.
      revealProfile(target);
      if (link.pathname !== location.pathname) {
        // The directory URL and index.html are the same home document.
        e.preventDefault();
        history.pushState(history.state, '', link.href);
        target.scrollIntoView();
      }
    });
  }

  function setupDeck(deck) {
    const slides = Array.from(deck.querySelectorAll('.slide'));
    const controls = deck.querySelector('.deck-controls');
    if (!controls) return;
    const video = deck.querySelector('video');
    const pause = controls.querySelector('[data-pause]');
    let movie = !!video && !motion.matches, paused = false, hovered = false, visible = false;
    let index = 0, clock, watchdog, trying = false, generation = 0;
    function slide() { slides.forEach((s, i) => { s.hidden = i !== index; }); }
    function active() {
      return visible && !document.hidden && !paused && !motion.matches && !hovered && !deck.matches(':focus-within');
    }
    function finish() {
      if (!movie) return;
      movie = false; video.pause(); video.hidden = true;
      index = 0; slide(); sync();
    }
    function guard() {
      clearTimeout(watchdog);
      if (movie && active()) watchdog = setTimeout(finish, 8000);
    }
    function sync() {
      clearTimeout(clock); clearTimeout(watchdog);
      controls.hidden = !movie && slides.length < 2;
      pause.hidden = motion.matches;
      pause.querySelector('[data-stop]').hidden = paused;
      pause.querySelector('[data-start]').hidden = !paused;
      if (!active()) {
        generation++; trying = false;
        if (video && !video.paused) video.pause();
        return;
      }
      if (movie) {
        if (!video.src) video.src = video.dataset.src;
        if (video.paused && !trying) {
          const run = ++generation;
          trying = true; video.muted = true;
          video.play().then(() => { if (generation === run) trying = false; }, () => {
            if (generation === run) { trying = false; finish(); }
          });
        }
        guard();
      } else if (slides.length > 1) {
        clock = setTimeout(() => { index = (index + 1) % slides.length; slide(); sync(); }, 4800);
      }
    }
    if (video) {
      video.addEventListener('playing', () => { if (movie) video.hidden = false; guard(); });
      video.addEventListener('timeupdate', guard);
      video.addEventListener('ended', finish);
      video.addEventListener('error', finish);
    }
    function step(delta) {
      if (movie) finish();
      else index = (index + slides.length + delta) % slides.length;
      slide(); sync();
    }
    controls.querySelector('[data-prev]').addEventListener('click', () => step(-1));
    controls.querySelector('[data-next]').addEventListener('click', () => step(1));
    pause.addEventListener('click', () => { paused = !paused; sync(); });
    deck.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') { hovered = true; sync(); } });
    deck.addEventListener('pointerleave', () => { hovered = false; sync(); });
    deck.addEventListener('focusin', sync);
    deck.addEventListener('focusout', () => queueMicrotask(sync));
    document.addEventListener('visibilitychange', sync);
    motion.addEventListener('change', () => { if (motion.matches && movie) finish(); sync(); });
    slide(); sync();
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }).observe(deck);
    }
    // Without visibility observation, manual image navigation is still available.
  }
  document.querySelectorAll('.deck').forEach(setupDeck);

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
