/**
 * Kid Activity Finder - Frontend
 */

const CATEGORY_LABELS = {
    library: "Bibliothèque",
    mjc: "MJC",
    theatre: "Théâtre",
};

let currentPage = 1;
let totalResults = 0;

// DOM elements
const filterCategory = document.getElementById("filter-category");
const filterCity = document.getElementById("filter-city");
const filterDateFrom = document.getElementById("filter-date-from");
const filterDateTo = document.getElementById("filter-date-to");
const filterAge = document.getElementById("filter-age");
const resultsContainer = document.getElementById("results");
const resultsCount = document.getElementById("results-count");
const loadMoreBtn = document.getElementById("load-more");
const emptyState = document.getElementById("empty-state");

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    // No default date filters — show all activities including those without dates
    await Promise.all([loadCities(), loadCategories()]);
    await fetchActivities();

    // Attach filter change handlers
    filterCategory.addEventListener("change", resetAndFetch);
    filterCity.addEventListener("change", resetAndFetch);
    filterDateFrom.addEventListener("change", resetAndFetch);
    filterDateTo.addEventListener("change", resetAndFetch);
    filterAge.addEventListener("change", resetAndFetch);

    loadMoreBtn.addEventListener("click", loadMore);
});

function formatDateISO(date) {
    return date.toISOString().split("T")[0];
}

async function loadCities() {
    try {
        const resp = await fetch("/api/cities");
        const cities = await resp.json();
        cities.forEach((city) => {
            const opt = document.createElement("option");
            opt.value = city;
            opt.textContent = city;
            filterCity.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load cities:", e);
    }
}

async function loadCategories() {
    try {
        const resp = await fetch("/api/categories");
        const categories = await resp.json();
        categories.forEach((cat) => {
            const opt = document.createElement("option");
            opt.value = cat;
            opt.textContent = CATEGORY_LABELS[cat] || cat;
            filterCategory.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load categories:", e);
    }
}

function resetAndFetch() {
    currentPage = 1;
    resultsContainer.innerHTML = "";
    fetchActivities();
}

async function fetchActivities() {
    const params = new URLSearchParams();
    if (filterCategory.value) params.set("category", filterCategory.value);
    if (filterCity.value) params.set("city", filterCity.value);
    if (filterDateFrom.value) params.set("date_from", filterDateFrom.value);
    if (filterDateTo.value) params.set("date_to", filterDateTo.value);
    if (filterAge.value) params.set("age", filterAge.value);
    params.set("page", currentPage);
    params.set("per_page", 20);

    try {
        const resp = await fetch(`/api/activities?${params}`);
        const data = await resp.json();

        totalResults = data.total;
        renderActivities(data.activities);
        updateResultsCount();
        updateLoadMoreButton(data);
    } catch (e) {
        console.error("Failed to fetch activities:", e);
        resultsContainer.innerHTML =
            '<p>Erreur lors du chargement des activités.</p>';
    }
}

function renderActivities(activities) {
    if (currentPage === 1 && activities.length === 0) {
        emptyState.style.display = "block";
        resultsCount.textContent = "";
    } else {
        emptyState.style.display = "none";
    }

    activities.forEach((act) => {
        const card = document.createElement("article");
        card.className = "activity-card";

        const badgeClass = `badge badge-${act.category}`;
        const categoryLabel = CATEGORY_LABELS[act.category] || act.category;

        const priceText = act.price || "Non renseigné";
        const priceClass =
            act.price && act.price.toLowerCase() === "gratuit"
                ? "price-tag price-free"
                : "price-tag";

        let dateDisplay = "";
        if (act.event_date) {
            const d = new Date(act.event_date + "T00:00:00");
            dateDisplay = d.toLocaleDateString("fr-FR", {
                weekday: "short",
                day: "numeric",
                month: "long",
                year: "numeric",
            });
        }
        if (act.event_time) {
            dateDisplay += ` à ${act.event_time}`;
        }

        const ageText = `${act.age_min}-${act.age_max} ans`;

        card.innerHTML = `
            <h3>${escapeHtml(act.title)}</h3>
            <div class="card-meta">
                <span class="${badgeClass}">${categoryLabel}</span>
                <span class="meta-item">${escapeHtml(act.city)}</span>
                ${dateDisplay ? `<span class="meta-item">${escapeHtml(dateDisplay)}</span>` : ""}
                <span class="meta-item">${ageText}</span>
            </div>
            ${act.summary ? `<p class="card-summary">${escapeHtml(act.summary)}</p>` : ""}
            <div class="card-footer">
                <span class="${priceClass}">${escapeHtml(priceText)}</span>
                ${act.link ? `<a href="${escapeHtml(act.link)}" target="_blank" rel="noopener">Voir &rarr;</a>` : ""}
            </div>
        `;

        resultsContainer.appendChild(card);
    });
}

function updateResultsCount() {
    const shown = resultsContainer.children.length;
    if (totalResults > 0) {
        resultsCount.textContent = `${shown} sur ${totalResults} activité${totalResults > 1 ? "s" : ""}`;
    } else {
        resultsCount.textContent = "";
    }
}

function updateLoadMoreButton(data) {
    const shown = resultsContainer.children.length;
    if (shown < data.total) {
        loadMoreBtn.style.display = "inline-block";
    } else {
        loadMoreBtn.style.display = "none";
    }
}

async function loadMore() {
    currentPage++;
    await fetchActivities();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
