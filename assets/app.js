(function () {
  const data = window.PLANTAO_DATA || { generatedAt: "", pages: [] };
  const categories = [
    { id: "all", label: "Todos" },
    { id: "uti", label: "UTI" },
    { id: "enfermaria", label: "Enfermaria" },
    { id: "centro-cirurgico", label: "Centro cirúrgico" },
    { id: "amib", label: "AMIB" },
    { id: "outros", label: "Outros" },
  ];

  const state = {
    filter: "all",
    query: "",
  };

  const cards = document.querySelector("#cards");
  const emptyState = document.querySelector("#empty-state");
  const resultCount = document.querySelector("#result-count");
  const resultTitle = document.querySelector("#result-title");
  const search = document.querySelector("#search");
  const chips = document.querySelector("#category-chips");
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const menuToggles = document.querySelectorAll("[data-menu-toggle]");
  const viewerPanel = document.querySelector("#viewer-panel");
  const viewerTitle = document.querySelector("#viewer-title");
  const viewerSubtitle = document.querySelector("#viewer-subtitle");
  const viewerOpen = document.querySelector("#viewer-open");
  const frame = document.querySelector("#plantao-frame");
  const previousButton = document.querySelector("[data-prev]");
  const nextButton = document.querySelector("[data-next]");
  const closeViewerButton = document.querySelector("[data-close-viewer]");
  const pages = data.pages || [];
  let activePath = "";

  const savedTheme = localStorage.getItem("plantao-theme");
  if (savedTheme) {
    document.documentElement.dataset.theme = savedTheme;
  }

  function normalize(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function categoryLabel(id) {
    return categories.find((category) => category.id === id)?.label || "Outros";
  }

  function filteredPages() {
    const query = normalize(state.query);
    return pages.filter((page) => {
      const matchesFilter = state.filter === "all" || page.category === state.filter;
      const haystack = normalize([
        page.title,
        page.path,
        page.categoryLabel,
        page.folder,
        page.summary,
      ].join(" "));
      return matchesFilter && (!query || haystack.includes(query));
    });
  }

  function updateCounts() {
    const totals = categories.reduce((acc, category) => {
      acc[category.id] = category.id === "all"
        ? pages.length
        : pages.filter((page) => page.category === category.id).length;
      return acc;
    }, {});

    Object.entries(totals).forEach(([id, count]) => {
      const node = document.querySelector(`#count-${id}`);
      if (node) node.textContent = count;
    });

    document.querySelector("#summary-total").textContent = pages.length;
    document.querySelector("#summary-categories").textContent = new Set(pages.map((page) => page.category)).size;
    document.querySelector("#summary-updated").textContent = data.generatedAt || "Hoje";
  }

  function renderChips() {
    chips.innerHTML = categories
      .map((category) => (
        `<button class="chip${category.id === state.filter ? " active" : ""}" type="button" data-filter="${category.id}">${category.label}</button>`
      ))
      .join("");
  }

  function renderCards() {
    const visible = filteredPages();
    cards.innerHTML = visible
      .map((page, index) => `
        <button class="plantao-card" type="button" data-open-path="${page.path}" data-visible-index="${index}">
          <div class="card-topline">
            <span class="category-badge">${page.categoryLabel}</span>
            <span class="path-badge">${page.folder || "raiz"}</span>
          </div>
          <h3>${page.title}</h3>
          <p>${page.summary}</p>
          <div class="card-meta">
            <span>Arquivo: ${page.path}</span>
            <span>Atualizado: ${page.updated || "não informado"}</span>
          </div>
        </button>
      `)
      .join("");

    const label = state.filter === "all" ? "Todos os plantões" : categoryLabel(state.filter);
    resultTitle.textContent = label;
    resultCount.textContent = `${visible.length} resultado${visible.length === 1 ? "" : "s"}`;
    emptyState.hidden = visible.length > 0;
    updateViewerButtons();
  }

  function activeVisibleIndex() {
    return filteredPages().findIndex((page) => page.path === activePath);
  }

  function openPage(path, shouldScroll = true) {
    const page = pages.find((item) => item.path === path);
    if (!page) return;

    activePath = page.path;
    viewerPanel.hidden = false;
    viewerTitle.textContent = page.title;
    viewerSubtitle.textContent = `${page.categoryLabel} · ${page.path}`;
    viewerOpen.href = page.href;
    frame.src = page.href;
    updateViewerButtons();

    const hash = `paciente=${encodeURIComponent(page.path)}`;
    history.replaceState(null, "", `#${hash}`);

    if (shouldScroll) {
      viewerPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function updateViewerButtons() {
    const visible = filteredPages();
    const index = activeVisibleIndex();
    previousButton.disabled = index <= 0;
    nextButton.disabled = index === -1 || index >= visible.length - 1;
  }

  function openSibling(direction) {
    const visible = filteredPages();
    const index = activeVisibleIndex();
    const nextPage = visible[index + direction];
    if (nextPage) openPage(nextPage.path);
  }

  function setFilter(filter) {
    state.filter = filter;
    document.querySelectorAll("[data-filter]").forEach((node) => {
      node.classList.toggle("active", node.dataset.filter === filter);
    });
    renderChips();
    renderCards();
    document.body.classList.remove("menu-open");
  }

  document.addEventListener("click", (event) => {
    const filterButton = event.target.closest("[data-filter]");
    if (filterButton) {
      event.preventDefault();
      setFilter(filterButton.dataset.filter);
    }

    const openButton = event.target.closest("[data-open-path]");
    if (openButton) {
      openPage(openButton.dataset.openPath);
    }
  });

  search.addEventListener("input", (event) => {
    state.query = event.target.value;
    renderCards();
  });

  themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem("plantao-theme", nextTheme);
  });

  menuToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      document.body.classList.toggle("menu-open");
    });
  });

  previousButton.addEventListener("click", () => openSibling(-1));
  nextButton.addEventListener("click", () => openSibling(1));
  closeViewerButton.addEventListener("click", () => {
    viewerPanel.hidden = true;
    frame.removeAttribute("src");
    activePath = "";
    history.replaceState(null, "", location.pathname);
  });

  updateCounts();
  renderChips();
  renderCards();

  const hashMatch = decodeURIComponent(location.hash).match(/paciente=(.+)$/);
  if (hashMatch) {
    openPage(hashMatch[1], false);
  }
})();
