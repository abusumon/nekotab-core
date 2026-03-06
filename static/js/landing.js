// NekoTab Landing — Interactions, dropdowns, animations
(function(){
  'use strict';

  // Year
  var yearEl = document.getElementById('em-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // ==================== MOBILE MENU ====================
  var burger = document.getElementById('em-burger');
  var menu = document.getElementById('em-mobile-menu');
  if (burger && menu) {
    burger.addEventListener('click', function() {
      var expanded = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!expanded));
      document.documentElement.classList.toggle('no-scroll', !expanded);
      if (expanded) {
        menu.classList.remove('open');
        setTimeout(function(){ menu.hidden = true; }, 280);
      } else {
        menu.hidden = false;
        requestAnimationFrame(function(){ menu.classList.add('open'); });
      }
    });
    menu.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        burger.setAttribute('aria-expanded', 'false');
        document.documentElement.classList.remove('no-scroll');
        menu.classList.remove('open');
        setTimeout(function(){ menu.hidden = true; }, 280);
      });
    });
  }

  // ==================== NAVBAR SCROLL ====================
  var nav = document.querySelector('.em-navbar');
  var backToTop = document.getElementById('em-back-to-top');

  function onScroll() {
    var y = window.scrollY;
    if (nav) {
      if (y > 10 && !nav.classList.contains('scrolled')) nav.classList.add('scrolled');
      if (y <= 10 && nav.classList.contains('scrolled')) nav.classList.remove('scrolled');
    }
    if (backToTop) {
      if (y > 600) backToTop.classList.add('visible');
      else backToTop.classList.remove('visible');
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll(); // run on load

  // ==================== BACK TO TOP ====================
  if (backToTop) {
    backToTop.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ==================== SMOOTH SCROLL ====================
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      var href = this.getAttribute('href');
      if (href === '#') return;
      var target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        var navHeight = nav ? nav.offsetHeight : 0;
        var top = target.getBoundingClientRect().top + window.scrollY - navHeight - 16;
        window.scrollTo({ top: top, behavior: 'smooth' });
        history.pushState(null, null, href);
      }
    });
  });

  // ==================== DROPDOWN NAVIGATION ====================
  var dropdowns = document.querySelectorAll('.em-nav-dropdown');
  var closeAllDropdowns = function() {
    dropdowns.forEach(function(dd) {
      dd.classList.remove('open');
      var trigger = dd.querySelector('.em-nav-dd-trigger');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  };

  dropdowns.forEach(function(dd) {
    var trigger = dd.querySelector('.em-nav-dd-trigger');
    if (!trigger) return;

    // Click toggle (for keyboard/touch)
    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      var isOpen = dd.classList.contains('open');
      closeAllDropdowns();
      if (!isOpen) {
        dd.classList.add('open');
        trigger.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.em-nav-dropdown')) {
      closeAllDropdowns();
    }
  });

  // Close dropdowns on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeAllDropdowns();
  });

  // ==================== FADE-IN ANIMATIONS ====================
  var animated = document.querySelectorAll(
    '.em-pillar, .em-feature-card, .em-usecase, .em-spotlight-card, ' +
    '.em-compare-card, .em-step, .em-format-card, .em-cred-card, .em-acc'
  );

  if ('IntersectionObserver' in window) {
    var animObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('em-in');
          animObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    animated.forEach(function(el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      animObs.observe(el);
    });
  }

  // ==================== SECTION FADE-IN ====================
  var sections = document.querySelectorAll('.em-section');
  if ('IntersectionObserver' in window && sections.length) {
    var secObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('em-in');
          secObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05 });

    sections.forEach(function(sec) {
      sec.style.opacity = '0';
      sec.style.transform = 'translateY(20px)';
      secObs.observe(sec);
    });
  }

  // ==================== REDUCED MOTION ====================
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    animated.forEach(function(el) {
      el.style.opacity = '1';
      el.style.transform = 'none';
    });
    sections.forEach(function(sec) {
      sec.style.opacity = '1';
      sec.style.transform = 'none';
    });
  }

})();
