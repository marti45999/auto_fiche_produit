const INITIAL_ROWS = 12;

const headerRow = document.getElementById("tableHeaderRow");
const tableBody = document.getElementById("tableBody");
const clearTableButton = document.getElementById("clearTableButton");
const addReplacementColumnButton = document.getElementById("addReplacementColumn");
const addRowButton = document.getElementById("addRowButton");

const BASE_HEADER_COUNT = headerRow.children.length;
let replacementColumnCount = 0;

function dataColumnCount() {
  return headerRow.children.length;
}

function createDataCell() {
  const td = document.createElement("td");
  td.contentEditable = "true";
  td.classList.add("data-cell");
  td.spellcheck = false;
  return td;
}

function createRow() {
  const row = document.createElement("tr");
  const columns = dataColumnCount();

  for (let i = 0; i < columns; i += 1) {
    row.appendChild(createDataCell());
  }

  tableBody.appendChild(row);
}

function initializeTable() {
  tableBody.innerHTML = "";
  for (let i = 0; i < INITIAL_ROWS; i += 1) {
    createRow();
  }
  refreshColumnIndices();
}

function refreshColumnIndices() {
  const rows = tableBody.querySelectorAll("tr");
  rows.forEach((row) => {
    const cells = row.querySelectorAll("td.data-cell");
    cells.forEach((cell, index) => {
      cell.dataset.colIndex = String(index);
    });
  });
}

function ensureRowExists(index) {
  while (tableBody.children.length <= index) {
    createRow();
  }
}

function ensureColumnExists(targetColumnCount) {
  while (
    dataColumnCount() < targetColumnCount &&
    replacementColumnCount < 1 &&
    targetColumnCount <= BASE_HEADER_COUNT + 1
  ) {
    addReplacementColumn();
  }
}

function detectDelimiter(line) {
  if (line.includes("\t")) {
    return "\t";
  }
  if (line.includes(";")) {
    return ";";
  }
  if (line.includes(",")) {
    return ",";
  }
  return "\t";
}

function cleanValue(value) {
  return value.replace(/\s+/gu, " ").trim();
}

function parseHtmlTable(html) {
  if (!html || !html.includes("<table")) {
    return null;
  }

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const table = doc.querySelector("table");
    if (!table) {
      return null;
    }

    const rows = [];
    Array.from(table.rows).forEach((row) => {
      const values = Array.from(row.cells).map((cell) => cleanValue(cell.textContent));
      if (values.some((value) => value.length > 0)) {
        rows.push(values);
      }
    });
    return rows.length ? rows : null;
  } catch {
    return null;
  }
}

function parsePlainText(text) {
  if (!text) {
    return [];
  }

  const normalized = text.replace(/\r\n/gu, "\n").replace(/\r/gu, "\n");
  const lines = normalized.split("\n").filter((line) => line.trim().length > 0);
  if (!lines.length) {
    return [];
  }

  const delimiter = detectDelimiter(lines[0]);
  return lines.map((line) =>
    line
      .split(delimiter)
      .map((value) => cleanValue(value.replace(/\n+/gu, " ")))
  );
}

function extractClipboardRows(event) {
  const clipboardData = event.clipboardData || window.clipboardData;
  const html = clipboardData.getData("text/html");
  const htmlRows = parseHtmlTable(html);
  if (htmlRows && htmlRows.length) {
    return htmlRows;
  }
  return parsePlainText(clipboardData.getData("text/plain"));
}

function handlePaste(event) {
  const target = event.target;
  if (!(target instanceof HTMLTableCellElement) || !target.classList.contains("data-cell")) {
    return;
  }

  event.preventDefault();
  const rowsData = extractClipboardRows(event);

  if (!rowsData.length) {
    return;
  }

  const startRow = target.parentElement;
  const startRowIndex = Array.from(tableBody.children).indexOf(startRow);
  const startColIndex = parseInt(target.dataset.colIndex ?? "0", 10);

  rowsData.forEach((lineValues, rowOffset) => {
    const targetRowIndex = startRowIndex + rowOffset;

    ensureRowExists(targetRowIndex);
    ensureColumnExists(startColIndex + lineValues.length);

    const row = tableBody.children[targetRowIndex];
    const cells = row.querySelectorAll("td.data-cell");

    lineValues.forEach((value, valueOffset) => {
      const colIndex = startColIndex + valueOffset;
      const cell = cells[colIndex];
      if (cell) {
        cell.textContent = value;
      }
    });
  });
}

function addReplacementColumn() {
  if (replacementColumnCount >= 1) {
    return;
  }

  replacementColumnCount = 1;
  const newHeader = document.createElement("th");
  newHeader.textContent = "Code EAN remplacement";
  newHeader.dataset.replacement = "1";
  headerRow.appendChild(newHeader);

  const rows = tableBody.querySelectorAll("tr");
  rows.forEach((row) => {
    const cell = createDataCell();
    cell.classList.add("replacement-cell");
    row.appendChild(cell);
  });

  addReplacementColumnButton.disabled = true;
  addReplacementColumnButton.classList.add("btn--disabled");
  refreshColumnIndices();
}

function clearTable() {
  replacementColumnCount = 0;

  headerRow
    .querySelectorAll("th[data-replacement='1']")
    .forEach((th) => th.remove());

  addReplacementColumnButton.disabled = false;
  addReplacementColumnButton.classList.remove("btn--disabled");

  initializeTable();
}

// ============================================================================
// SCRAPING LOGIC
// ============================================================================

const startScrapingButton = document.getElementById("startScrapingButton");
const statusSection = document.getElementById("statusSection");
const statusMessage = document.getElementById("statusMessage");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const resultsSection = document.getElementById("resultsSection");
const resultsContent = document.getElementById("resultsContent");

const EAN_COLUMN_INDEX = 6; // Code barre (7ème colonne, index 6)

function extractEANsFromTable() {
  const eans = [];
  const ignored3400 = [];
  const rows = tableBody.querySelectorAll("tr");

  rows.forEach((row) => {
    const cells = row.querySelectorAll("td.data-cell");
    const primaryEanCell = cells[EAN_COLUMN_INDEX];

    if (!primaryEanCell) {
      return;
    }

    const primaryEan = primaryEanCell.textContent.trim();

    if (!primaryEan || primaryEan.length === 0) {
      return;
    }

    // Filtrer les EAN commençant par "3400"
    if (primaryEan.startsWith("3400")) {
      ignored3400.push(primaryEan);
      return;
    }

    // Chercher le code EAN de remplacement (dernière colonne si elle existe)
    const replacementCell = cells[cells.length - 1];
    let replacementEan = null;

    // Vérifier si la dernière cellule est une cellule de remplacement
    if (replacementCell && replacementCell.classList.contains("replacement-cell")) {
      const value = replacementCell.textContent.trim();
      if (value && value.length > 0) {
        replacementEan = value;
      }
    }

    eans.push({
      primary: primaryEan,
      replacement: replacementEan,
    });
  });

  return { eans, ignored3400 };
}

async function startScraping() {
  const { eans, ignored3400 } = extractEANsFromTable();

  if (eans.length === 0 && ignored3400.length === 0) {
    alert("❌ Aucun code EAN trouvé dans le tableau. Veuillez remplir la colonne 'Code barre'.");
    return;
  }

  // Afficher le statut
  statusSection.style.display = "block";
  resultsSection.style.display = "none";
  statusMessage.textContent = `🔄 Scraping en cours pour ${eans.length} produit(s)... (${ignored3400.length} produit(s) ignoré(s) commençant par 3400)`;
  progressFill.style.width = "0%";
  startScrapingButton.disabled = true;
  startScrapingButton.classList.add("btn--disabled");

  try {
    const response = await fetch("/api/scrape", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ eans, ignored3400 }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Erreur inconnue");
    }

    const data = await response.json();

    // Mode asynchrone : réponse 202 (Accepted)
    if (response.status === 202) {
      progressFill.style.width = "50%";
      statusMessage.textContent = `✅ Scraping lancé en arrière-plan ! ${data.total_products} produit(s) en cours de traitement.\n\n📤 Les webhooks seront envoyés au fur et à mesure (consultez les logs du serveur pour suivre la progression).`;

      // Message d'information supplémentaire
      resultsSection.style.display = "block";
      resultsContent.innerHTML = `
        <div class="result-card">
          <h3>ℹ️ Mode Asynchrone</h3>
          <p>Le scraping a été lancé en arrière-plan avec succès.</p>
          <p><strong>Produits à traiter :</strong> ${data.total_products}</p>
          <p><strong>Thread ID :</strong> ${data.thread_id || 'N/A'}</p>
          <br>
          <p>Les webhooks seront envoyés progressivement à n8n au fur et à mesure du traitement de chaque produit.</p>
          <p>Consultez les logs du serveur pour suivre la progression en temps réel :</p>
          <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">tail -f server_async.log</pre>
        </div>
      `;
    } else {
      // Mode synchrone (ancien comportement avec résultats)
      progressFill.style.width = "100%";
      statusMessage.textContent = `✅ Scraping terminé ! ${data.total_processed} produit(s) traité(s).`;

      // Afficher les résultats
      if (data.results) {
        displayResults(data.results);
      }
    }
  } catch (error) {
    statusMessage.textContent = `❌ Erreur : ${error.message}`;
    console.error("Erreur lors du scraping:", error);
  } finally {
    startScrapingButton.disabled = false;
    startScrapingButton.classList.remove("btn--disabled");
  }
}

function displayResults(results) {
  resultsSection.style.display = "block";
  resultsContent.innerHTML = "";

  results.forEach((result, index) => {
    const resultCard = document.createElement("div");
    resultCard.className = "result-card";

    let html = `<h3>Produit ${index + 1} - EAN: ${result.primary_ean}</h3>`;

    if (result.replacement_ean) {
      html += `<p class="replacement-info">🔄 Code de remplacement: ${result.replacement_ean}</p>`;
    }

    if (!result.found) {
      html += `<p class="not-found">❌ Produit non trouvé sur aucun site</p>`;
    } else {
      const productEntries = Object.values(result.products);

      productEntries.forEach((product) => {
        const usedReplacement = product.used_replacement ? " (via code de remplacement)" : "";

        html += `
          <div class="product-info">
            <h4>🏪 ${product.site}${usedReplacement}</h4>
            <p><strong>Titre:</strong> ${product.titre || "N/A"}</p>
            <p><strong>Prix:</strong> ${product.prix || "N/A"}</p>
            ${product.ean_verif ? `<p><strong>EAN vérifié:</strong> ${product.ean_verif}</p>` : ""}
            ${product.reference ? `<p><strong>Référence:</strong> ${product.reference}</p>` : ""}
            ${product.note ? `<p><strong>Note:</strong> ${product.note}</p>` : ""}
            <p><strong>URL:</strong> <a href="${product.url}" target="_blank">${product.url}</a></p>
          </div>
        `;
      });
    }

    resultCard.innerHTML = html;
    resultsContent.appendChild(resultCard);
  });
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

tableBody.addEventListener("paste", handlePaste);
clearTableButton.addEventListener("click", clearTable);
addReplacementColumnButton.addEventListener("click", addReplacementColumn);
addRowButton.addEventListener("click", () => {
  createRow();
  refreshColumnIndices();
});
startScrapingButton.addEventListener("click", startScraping);

initializeTable();
