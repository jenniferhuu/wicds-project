const labels = {
  acne_prone: "Acne prone",
  excess_oil: "Excess oil",
  dark_spots: "Dark spots",
  fine_lines: "Fine lines",
  sun_damage: "Sun damage",
  dark_circles: "Dark circles",
  essential_oils: "Essential oils",
  salicylic_acid: "Salicylic acid",
  vitamin_c: "Vitamin C",
  coconut_oil: "Coconut oil",
};

const titleize = (value) =>
  labels[value] || value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());

const form = document.querySelector("#profile-form");
const statusPill = document.querySelector("#status-pill");
const summaryTitle = document.querySelector("#summary-title");
const insights = document.querySelector("#insights");
const amRoutine = document.querySelector("#am-routine");
const pmRoutine = document.querySelector("#pm-routine");

async function init() {
  const [optionsResponse, healthResponse] = await Promise.all([
    fetch("/api/options"),
    fetch("/api/health"),
  ]);
  const options = await optionsResponse.json();
  const health = await healthResponse.json();

  fillSelect("skin-type", options.skin_types, "combination");
  fillSelect("age-range", options.age_ranges, "30s");
  fillSelect("climate", options.climates, "temperate");
  fillSelect("budget", options.budgets, "any");
  fillSelect("sensitivity-level", options.sensitivity_levels, "normal");
  fillChips("concerns", options.concerns, ["acne", "dullness", "fine_lines"]);
  fillChips("allergies", options.allergies, []);

  statusPill.textContent = `${health.products} products loaded`;
  await submitProfile();
}

function fillSelect(id, values, selected) {
  const select = document.querySelector(`#${id}`);
  select.innerHTML = values
    .map((value) => `<option value="${value}" ${value === selected ? "selected" : ""}>${titleize(value)}</option>`)
    .join("");
}

function fillChips(id, values, selectedValues) {
  const selected = new Set(selectedValues);
  document.querySelector(`#${id}`).innerHTML = values
    .map(
      (value) => `
      <label class="chip">
        <input type="checkbox" value="${value}" ${selected.has(value) ? "checked" : ""} />
        <span>${titleize(value)}</span>
      </label>`
    )
    .join("");
}

function getChecked(id) {
  return Array.from(document.querySelectorAll(`#${id} input:checked`)).map((input) => input.value);
}

function payloadFromForm() {
  const data = new FormData(form);
  return {
    skin_type: data.get("skin_type"),
    age_range: data.get("age_range"),
    climate: data.get("climate"),
    budget: data.get("budget"),
    sensitivity_level: data.get("sensitivity_level"),
    pregnancy: data.get("pregnancy") === "on",
    concerns: getChecked("concerns"),
    allergies: getChecked("allergies"),
  };
}

async function submitProfile(event) {
  event?.preventDefault();
  setLoading(true);
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payloadFromForm()),
  });
  const result = await response.json();
  setLoading(false);

  if (!response.ok) {
    summaryTitle.textContent = result.error || "Something went wrong";
    return;
  }

  renderResult(result);
}

function setLoading(isLoading) {
  form.querySelector("button[type='submit']").textContent = isLoading ? "Building..." : "Build routine";
}

function renderResult(result) {
  const profile = result.user_profile;
  summaryTitle.textContent = `${titleize(profile.skin_type)} skin with ${profile.effective_concerns
    .slice(0, 3)
    .map(titleize)
    .join(", ")}`;

  insights.innerHTML = [
    ["Effective concerns", profile.effective_concerns.map(titleize).join(", ") || "None"],
    ["Safety filters", profile.effective_avoid_conditions.map(titleize).join(", ") || "Standard"],
    ["Model layer", "Cosine ranking plus rule-based routine assembly"],
  ]
    .map(([label, value]) => `<div class="insight"><strong>${label}</strong><span>${value}</span></div>`)
    .join("");

  renderRoutine(amRoutine, result.am_routine, result.am_validation);
  renderRoutine(pmRoutine, result.pm_routine, result.pm_validation);
}

function renderRoutine(container, products, validation) {
  if (!products.length) {
    container.className = "routine-list empty-state";
    container.textContent = "No routine could be assembled with these constraints.";
    return;
  }

  container.className = "routine-list";
  const warnings = validation.warnings?.length
    ? `<div class="product"><p>${validation.warnings.join(" ")}</p></div>`
    : "";
  container.innerHTML =
    products
      .map(
        (product, index) => `
      <div class="product">
        <div class="product-top">
          <div>
            <div class="category">${index + 1}. ${titleize(product.category)}</div>
            <h4>${product.name}</h4>
            <p>${product.brand} · $${product.price} · ${titleize(product.price_range)}</p>
          </div>
          <div class="score">${Math.round(product.similarity_score * 100)}%</div>
        </div>
        <div class="reason-list">
          ${product.match_reasons.map((reason) => `<span>${reason}</span>`).join("")}
        </div>
      </div>`
      )
      .join("") + warnings;
}

document.querySelector("#demo-profile").addEventListener("click", () => {
  fillSelect("skin-type", ["acne_prone", "combination", "dry", "normal", "oily", "sensitive"], "acne_prone");
  fillSelect("age-range", ["teens", "20s", "30s", "40s", "50s", "60+"], "20s");
  fillSelect("climate", ["cold", "dry", "humid", "temperate", "tropical"], "humid");
  fillSelect("budget", ["any", "budget", "mid", "premium"], "mid");
  fillSelect("sensitivity-level", ["low", "normal", "high"], "normal");
  document.querySelectorAll("#concerns input").forEach((input) => {
    input.checked = ["acne", "blackheads", "excess_oil", "pores"].includes(input.value);
  });
  document.querySelectorAll("#allergies input").forEach((input) => {
    input.checked = input.value === "fragrance";
  });
  submitProfile();
});

form.addEventListener("submit", submitProfile);
init().catch((error) => {
  statusPill.textContent = "Model failed to load";
  summaryTitle.textContent = error.message;
});
