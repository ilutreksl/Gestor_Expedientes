(function () {
  "use strict";

  var DOCS = window.WIKI_DOCS || {};
  var contentEl = document.getElementById("wiki-content");
  var tocEl = document.getElementById("wiki-toc");
  var searchEl = document.getElementById("wiki-search");
  var tabButtons = document.querySelectorAll(".tab-btn");

  var renderedCache = {};
  var tocTreeCache = {};
  var currentDoc = null;

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function slugify(str) {
    return String(str)
      .toLowerCase()
      .replace(/`/g, "")
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .trim()
      .replace(/\s+/g, "-");
  }

  function buildRenderer() {
    var renderer = new marked.Renderer();
    var counts = {};
    var headings = [];
    renderer.heading = function (text, level, raw) {
      var slug = slugify(raw) || "seccion";
      if (counts[slug] != null) {
        counts[slug] += 1;
        slug = slug + "-" + counts[slug];
      } else {
        counts[slug] = 0;
      }
      headings.push({ level: level, text: raw, slug: slug });
      return '<h' + level + ' id="' + slug + '">' + text + '</h' + level + '>\n';
    };
    return { renderer: renderer, headings: headings };
  }

  function buildTocTree(headings) {
    var tree = [];
    var current = null;
    headings.forEach(function (h) {
      if (h.level === 2) {
        current = { text: h.text, slug: h.slug, children: [] };
        tree.push(current);
      } else if (h.level === 3 && current) {
        current.children.push(h);
      }
    });
    return tree;
  }

  function renderDoc(key) {
    if (renderedCache[key]) return renderedCache[key];
    var built = buildRenderer();
    var html = marked.parse(DOCS[key].md, { renderer: built.renderer, gfm: true });
    renderedCache[key] = html;
    tocTreeCache[key] = buildTocTree(built.headings);
    return html;
  }

  function renderTocTree(tree, query) {
    var q = (query || "").trim().toLowerCase();
    var html = '<ul class="toc-list">';
    tree.forEach(function (node) {
      var childMatches = node.children.filter(function (c) {
        return !q || c.text.toLowerCase().indexOf(q) !== -1;
      });
      var selfMatches = !q || node.text.toLowerCase().indexOf(q) !== -1;
      if (!selfMatches && childMatches.length === 0) return;

      html += '<li><a href="#' + node.slug + '" data-slug="' + node.slug + '">' + escapeHtml(node.text) + "</a>";
      var childList = q ? (selfMatches ? node.children : childMatches) : node.children;
      if (childList.length) {
        html += '<ul class="toc-sub">';
        childList.forEach(function (c) {
          html += '<li><a href="#' + c.slug + '" data-slug="' + c.slug + '">' + escapeHtml(c.text) + "</a></li>";
        });
        html += "</ul>";
      }
      html += "</li>";
    });
    html += "</ul>";
    return html;
  }

  function showDoc(key) {
    currentDoc = key;
    contentEl.innerHTML = renderDoc(key);
    searchEl.value = "";
    tocEl.innerHTML = renderTocTree(tocTreeCache[key], "");
    tabButtons.forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-doc") === key);
    });
    contentEl.scrollTop = 0;
  }

  tabButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      showDoc(btn.getAttribute("data-doc"));
    });
  });

  searchEl.addEventListener("input", function () {
    tocEl.innerHTML = renderTocTree(tocTreeCache[currentDoc], searchEl.value);
  });

  tocEl.addEventListener("click", function (e) {
    var a = e.target.closest("a[data-slug]");
    if (!a) return;
    e.preventDefault();
    var target = document.getElementById(a.getAttribute("data-slug"));
    if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  showDoc("manual");
})();
