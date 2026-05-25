(function () {
  const data = window.PLANTAO_DATA || { generatedAt: "", pages: [] };
  const categories = [
    { id: "all", label: "Todos" },
    { id: "uti", label: "UTI" },
    { id: "enfermaria", label: "Enfermaria" },
    { id: "centro-cirurgico", label: "Centro cirúrgico" },
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
  const visitCounter = document.querySelector("#visit-counter");
  const visitCounterNote = document.querySelector("#visit-counter-note");
  const pages = data.pages || [];
  const hasDashboard = Boolean(
    cards
      && emptyState
      && resultCount
      && resultTitle
      && search
      && chips
      && viewerPanel
      && viewerTitle
      && viewerSubtitle
      && viewerOpen
      && frame
      && previousButton
      && nextButton
      && closeViewerButton
  );
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

  function slugify(value) {
    return normalize(value)
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "pagina";
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
        page.shiftDate,
        page.shiftDateLabel,
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

    const archivedDates = [...new Set(pages.map((page) => page.shiftDate).filter(Boolean))];
    const latestShift = archivedDates.slice().sort((left, right) => right.localeCompare(left, "pt-BR"))[0];

    document.querySelector("#summary-total").textContent = pages.length;
    document.querySelector("#summary-categories").textContent = new Set(pages.map((page) => page.category)).size;
    document.querySelector("#summary-updated").textContent = pages.find((page) => page.shiftDate === latestShift)?.shiftDateLabel || data.generatedAt || "Hoje";

    const summaryShifts = document.querySelector("#summary-shifts");
    if (summaryShifts) {
      summaryShifts.textContent = archivedDates.length;
    }
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
            <span class="date-badge">${page.shiftDateLabel || "Sem data"}</span>
          </div>
          <h3>${page.title}</h3>
          <p>${page.summary}</p>
          <div class="card-meta">
            <span>Plantão: ${page.shiftDateLabel || "não informado"}</span>
            <span>Pasta: ${page.folder || "raiz"}</span>
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
    viewerSubtitle.textContent = [page.categoryLabel, page.shiftDateLabel, page.path].filter(Boolean).join(" · ");
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
    if (filterButton && hasDashboard) {
      event.preventDefault();
      setFilter(filterButton.dataset.filter);
    }

    const openButton = event.target.closest("[data-open-path]");
    if (openButton && hasDashboard) {
      openPage(openButton.dataset.openPath);
    }
  });

  if (search) {
    search.addEventListener("input", (event) => {
      state.query = event.target.value;
      renderCards();
    });
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = nextTheme;
      localStorage.setItem("plantao-theme", nextTheme);
    });
  }

  menuToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      document.body.classList.toggle("menu-open");
    });
  });

  if (previousButton) {
    previousButton.addEventListener("click", () => openSibling(-1));
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => openSibling(1));
  }

  if (closeViewerButton) {
    closeViewerButton.addEventListener("click", () => {
      viewerPanel.hidden = true;
      frame.removeAttribute("src");
      activePath = "";
      history.replaceState(null, "", location.pathname);
    });
  }

  async function loadVisitCounter() {
    if (!visitCounter || !visitCounterNote) return;

    const localHosts = new Set(["", "localhost", "127.0.0.1", "::1"]);
    const isLocalPreview = location.protocol === "file:" || localHosts.has(location.hostname);

    if (isLocalPreview) {
      visitCounter.textContent = "Preview";
      visitCounterNote.textContent = "O contador passa a registrar visitas automaticamente no site publicado.";
      return;
    }

    const namespace = "dr-fernando-dashboard";
    const counterName = slugify(`${location.hostname}-${location.pathname}`);
    const sessionKey = `visit-counter:${counterName}`;
    const alreadyCounted = sessionStorage.getItem(sessionKey) === "1";
    const endpoint = `https://api.counterapi.dev/v1/${namespace}/${counterName}${alreadyCounted ? "" : "/up"}`;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(endpoint, {
        method: "GET",
        mode: "cors",
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Counter request failed with status ${response.status}`);
      }

      const result = await response.json();
      const total = Number(result.count || 0);
      visitCounter.textContent = new Intl.NumberFormat("pt-BR").format(total);
      visitCounterNote.textContent = alreadyCounted
        ? "Você já foi contabilizado nesta sessão; o número acima mostra o total público acumulado."
        : "Contador público de acessos desta página, atualizado automaticamente.";

      if (!alreadyCounted) {
        sessionStorage.setItem(sessionKey, "1");
      }
    } catch (error) {
      console.error("Visit counter unavailable:", error);
      visitCounter.textContent = "Indisponível";
      visitCounterNote.textContent = "Não foi possível consultar o contador agora.";
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  if (hasDashboard) {
    updateCounts();
    renderChips();
    renderCards();
  }

  loadVisitCounter();

  const hashMatch = decodeURIComponent(location.hash).match(/paciente=(.+)$/);
  if (hashMatch && hasDashboard) {
    openPage(hashMatch[1], false);
  }
})();
