/* keprix marketing site - vanilla JS */

(function () {
  "use strict";

  // FAQ accordion
  document.querySelectorAll(".faq-q").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var item = btn.closest(".faq-item");
      var isOpen = item.classList.contains("open");
      document.querySelectorAll(".faq-item.open").forEach(function (el) {
        el.classList.remove("open");
      });
      if (!isOpen) {
        item.classList.add("open");
      }
    });
  });

  // Sticky header scroll class
  var header = document.querySelector(".site-header");
  if (header) {
    window.addEventListener("scroll", function () {
      header.classList.toggle("scrolled", window.scrollY > 16);
    }, { passive: true });
  }

  // Mobile nav toggle
  var navToggle = document.querySelector(".nav-toggle");
  var navMobile = document.querySelector(".nav-mobile");
  if (navToggle && navMobile) {
    navToggle.addEventListener("click", function () {
      var open = navMobile.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }
})();
