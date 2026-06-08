// NekoTab Landing — Interactions, dropdowns, animations
(function(){
  'use strict';

  // Year
  var yearEl = document.getElementById('em-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // ==================== MOBILE MENU ====================
  var burger = document.getElementById('em-burger');
  var menu = document.getElementById('em-mobile-menu');
  var backdrop = document.getElementById('em-mobile-backdrop');
  var closeBtn = document.getElementById('em-menu-close');

  function openMobileMenu() {
    burger.setAttribute('aria-expanded', 'true');
    document.documentElement.classList.add('no-scroll');
    menu.removeAttribute('hidden');
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        menu.classList.add('open');
        if (backdrop) backdrop.classList.add('open');
      });
    });
  }

  function closeMobileMenu() {
    burger.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('no-scroll');
    menu.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    setTimeout(function() {
      if (!menu.classList.contains('open')) { menu.setAttribute('hidden', ''); }
    }, 340);
  }

  if (burger && menu) {
    burger.addEventListener('click', function() {
      if (burger.getAttribute('aria-expanded') === 'true') {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });
    if (backdrop) backdrop.addEventListener('click', closeMobileMenu);
    if (closeBtn) closeBtn.addEventListener('click', closeMobileMenu);
    menu.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', closeMobileMenu);
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

  // ==================== NESTED FLYOUT (Tab Room) ====================
  var nestedTriggers = document.querySelectorAll('.em-dd-nested-trigger');
  nestedTriggers.forEach(function(trigger) {
    trigger.addEventListener('click', function(e) {
      e.stopPropagation();
      var nested = trigger.closest('.em-dd-nested');
      if (!nested) return;
      var isOpen = nested.classList.contains('open');
      // Close all nested flyouts first
      document.querySelectorAll('.em-dd-nested.open').forEach(function(n) {
        n.classList.remove('open');
        var t = n.querySelector('.em-dd-nested-trigger');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
      if (!isOpen) {
        nested.classList.add('open');
        trigger.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // Close nested flyouts when clicking outside
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.em-dd-nested')) {
      document.querySelectorAll('.em-dd-nested.open').forEach(function(n) {
        n.classList.remove('open');
        var t = n.querySelector('.em-dd-nested-trigger');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
    }
  });

  // ==================== MOBILE ACCORDION (Tab Room) ====================
  var accordionTriggers = document.querySelectorAll('.em-mobile-accordion-trigger');
  accordionTriggers.forEach(function(trigger) {
    trigger.addEventListener('click', function() {
      var panel = trigger.nextElementSibling;
      if (!panel || !panel.classList.contains('em-mobile-accordion-panel')) return;
      var isOpen = trigger.getAttribute('aria-expanded') === 'true';
      trigger.setAttribute('aria-expanded', String(!isOpen));
      panel.hidden = isOpen;
    });
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
