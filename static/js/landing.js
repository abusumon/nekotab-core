// Landing page interactions & micro-animations
(function(){
  const yearEl = document.getElementById('em-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Mobile menu toggle
  const burger = document.getElementById('em-burger');
  const menu = document.getElementById('em-mobile-menu');
  if (burger && menu) {
    burger.addEventListener('click', () => {
      const expanded = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!expanded));
      document.documentElement.classList.toggle('no-scroll', !expanded);
      if (expanded) {
        menu.classList.remove('open');
        setTimeout(()=>{ menu.hidden = true; }, 280);
      } else {
        menu.hidden = false;
        requestAnimationFrame(()=> menu.classList.add('open'));
      }
    });
    // Close mobile menu when clicking a link
    menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        burger.setAttribute('aria-expanded', 'false');
        document.documentElement.classList.remove('no-scroll');
        menu.classList.remove('open');
        setTimeout(() => { menu.hidden = true; }, 280);
      });
    });
  }

  // Navbar shadow on scroll + back-to-top visibility
  const nav = document.querySelector('.em-navbar');
  const backToTop = document.getElementById('em-back-to-top');
  const onScroll = () => {
    const y = window.scrollY;
    if (nav) {
      if (y > 10 && !nav.classList.contains('scrolled')) nav.classList.add('scrolled');
      if (y <= 10 && nav.classList.contains('scrolled')) nav.classList.remove('scrolled');
    }
    // Show/hide back-to-top button
    if (backToTop) {
      if (y > 600) backToTop.classList.add('visible');
      else backToTop.classList.remove('visible');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });

  // Back-to-top click
  if (backToTop) {
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Update URL without jumping
        history.pushState(null, null, this.getAttribute('href'));
      }
    });
  });

  // Simple stat count-up when visible
  const nums = document.querySelectorAll('.em-num');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.getAttribute('data-target'), 10);
        if (!el.dataset.done) {
          let current = 0; const step = Math.ceil(target / 60);
          const tick = () => { current += step; if (current >= target) { current = target; el.textContent = current + (target < 10 ? 'x' : '+'); el.dataset.done = 'true'; return; } el.textContent = current; requestAnimationFrame(tick); };
          requestAnimationFrame(tick);
        }
      }
    });
  }, { threshold: 0.3 });
  nums.forEach(n => observer.observe(n));

  // Fade-up animation on scroll
  const animated = document.querySelectorAll('.em-section, .em-feature-card, .em-tool-card, .em-card, .em-box, .em-spotlight-card');
  const animObs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('em-in');
      }
    });
  }, { threshold: 0.1 });
  animated.forEach(a => { a.style.opacity = 0; a.style.transform = 'translateY(24px)'; animObs.observe(a); });
  const style = document.createElement('style');
  style.textContent = '.em-in{opacity:1!important;transform:translateY(0)!important;transition:opacity .6s ease-out, transform .6s ease-out;}';
  document.head.appendChild(style);
})();
