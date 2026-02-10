// Document AI - Modern Web App with Multi-Document & Excel Export
const API = ""; // same origin
const HISTORY_KEY = "documentAI_history";

// State
let selectedFiles = [];
let extractionResults = [];
let processingHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");

// User & Logout
const userEmailEl = document.getElementById("userEmail");
const btnLogout = document.getElementById("btnLogout");

// Display user email
const storedUser = localStorage.getItem("docai_user");
if (storedUser) {
  try {
    const user = JSON.parse(storedUser);
    if (userEmailEl) userEmailEl.textContent = user.email || user.name || "";
  } catch (e) { }
}

// Logout handler
if (btnLogout) {
  btnLogout.addEventListener("click", () => {
    localStorage.removeItem("docai_user");
    window.location.href = "/login.html";
  });
}

// DOM Elements
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const fileCount = document.getElementById("fileCount");
const btnExtract = document.getElementById("btnExtract");
const btnClear = document.getElementById("btnClear");
const statusMessage = document.getElementById("statusMessage");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const resultsCard = document.getElementById("resultsCard");
const statsGrid = document.getElementById("statsGrid");
const resultsContainer = document.getElementById("resultsContainer");
const btnExportExcel = document.getElementById("btnExportExcel");
const rotationSection = document.getElementById("rotationSection");
const rotationSelect = document.getElementById("rotationSelect");
const documentTypeSelect = document.getElementById("documentTypeSelect");
const historyContainer = document.getElementById("historyContainer");
const batchProgress = document.getElementById("batchProgress");
const batchStats = document.getElementById("batchStats");
const batchFileList = document.getElementById("batchFileList");
const btnRetryFailed = document.getElementById("btnRetryFailed");
const btnClearHistory = document.getElementById("btnClearHistory");

// File Upload Handlers
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", () => {
  handleFiles(fileInput.files);
});

function handleFiles(files) {
  for (const file of files) {
    if (!selectedFiles.find(f => f.name === file.name)) {
      selectedFiles.push(file);
    }
  }
  updateFileList();
}

function updateFileList() {
  fileCount.textContent = `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} selected`;
  btnExtract.disabled = selectedFiles.length === 0;
  btnClear.disabled = selectedFiles.length === 0;

  if (selectedFiles.length === 0) {
    fileList.classList.add("hidden");
    rotationSection.classList.add("hidden");
    return;
  }

  // Show rotation option if any image files are selected
  const hasImages = selectedFiles.some(f => /\.(jpg|jpeg|png|tiff|tif)$/i.test(f.name));
  if (hasImages) {
    rotationSection.classList.remove("hidden");
  } else {
    rotationSection.classList.add("hidden");
  }

  fileList.classList.remove("hidden");

  // Create file items with thumbnail previews
  fileList.innerHTML = selectedFiles.map((file, index) => {
    const isImage = /\.(jpg|jpeg|png|tiff|tif)$/i.test(file.name);
    const isPdf = /\.pdf$/i.test(file.name);

    return `
    <div class="file-item" data-index="${index}">
      <div class="file-info">
        <div class="file-thumbnail" id="thumb-${index}" style="width: 48px; height: 48px; border-radius: 6px; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0;">
          ${isPdf ? `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15h6"></path><path d="M9 11h6"></path></svg>` :
        `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`}
        </div>
        <div style="flex: 1; min-width: 0;">
          <div class="file-name">${file.name}</div>
          <div class="file-size">${formatFileSize(file.size)}</div>
        </div>
      </div>
      <button class="file-remove" data-index="${index}">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  `}).join("");

  // Generate thumbnails for image files
  selectedFiles.forEach((file, index) => {
    if (/\.(jpg|jpeg|png|tiff|tif)$/i.test(file.name)) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const thumbEl = document.getElementById(`thumb-${index}`);
        if (thumbEl) {
          thumbEl.innerHTML = `<img src="${e.target.result}" style="width: 100%; height: 100%; object-fit: cover;" alt="Preview">`;
        }
      };
      reader.readAsDataURL(file);
    }
  });

  // Add remove handlers
  fileList.querySelectorAll(".file-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      const index = parseInt(btn.dataset.index);
      selectedFiles.splice(index, 1);
      updateFileList();
    });
  });
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// Clear All Handler
btnClear.addEventListener("click", () => {
  selectedFiles = [];
  extractionResults = [];
  updateFileList();
  resultsCard.classList.add("hidden");
  hideStatus();
});

// Extract Handler
btnExtract.addEventListener("click", async () => {
  if (selectedFiles.length === 0) return;

  extractionResults = [];
  const totalFiles = selectedFiles.length;
  const isBatch = totalFiles > 1;

  showStatus("loading", `Processing ${totalFiles} document${totalFiles > 1 ? 's' : ''}...`);
  progressBar.classList.remove("hidden");
  btnExtract.disabled = true;
  btnExtract.innerHTML = '<div class="spinner"></div> Extracting...';

  // Initialize batch tracking
  const fileStatuses = selectedFiles.map((f, i) => ({ index: i, file: f, status: 'pending', error: null }));

  if (isBatch && batchProgress) {
    batchProgress.classList.remove("hidden");
    if (btnRetryFailed) btnRetryFailed.classList.add("hidden");
  }

  function renderBatchUI() {
    if (!isBatch || !batchProgress) return;
    const done = fileStatuses.filter(f => f.status === 'done').length;
    const failed = fileStatuses.filter(f => f.status === 'failed').length;
    const processing = fileStatuses.filter(f => f.status === 'processing').length;
    const pending = fileStatuses.filter(f => f.status === 'pending').length;

    if (batchStats) {
      batchStats.innerHTML = `
        <div class="batch-stat"><div class="batch-stat-value">${done + failed}/${totalFiles}</div><div class="batch-stat-label">Completed</div></div>
        <div class="batch-stat"><div class="batch-stat-value" style="color: var(--accent-success);">${done}</div><div class="batch-stat-label">Successful</div></div>
        <div class="batch-stat"><div class="batch-stat-value" style="color: var(--accent-danger);">${failed}</div><div class="batch-stat-label">Failed</div></div>
        <div class="batch-stat"><div class="batch-stat-value">${pending + processing}</div><div class="batch-stat-label">Remaining</div></div>
      `;
    }

    if (batchFileList) {
      batchFileList.innerHTML = fileStatuses.map(fs => {
        const icon = fs.status === 'done' ? '\u2705' : fs.status === 'failed' ? '\u274c' : fs.status === 'processing' ? '<span class="batch-spinner">\u2699\ufe0f</span>' : '\u23f3';
        const statusText = fs.status === 'processing' ? 'Extracting...' : fs.status === 'done' ? 'Complete' : fs.status === 'failed' ? (fs.error || 'Failed') : 'Pending';
        return `<div class="batch-item ${fs.status}"><span class="batch-icon">${icon}</span><span class="batch-name">${fs.file.name}</span><span class="batch-status">${statusText}</span></div>`;
      }).join('');
    }
  }

  renderBatchUI();

  for (let i = 0; i < selectedFiles.length; i++) {
    fileStatuses[i].status = 'processing';
    renderBatchUI();
    progressFill.style.width = `${((i) / selectedFiles.length) * 100}%`;

    try {
      const result = await extractDocument(selectedFiles[i]);
      extractionResults.push({ file: selectedFiles[i].name, success: true, data: result });
      fileStatuses[i].status = 'done';
    } catch (err) {
      extractionResults.push({ file: selectedFiles[i].name, success: false, error: err.message });
      fileStatuses[i].status = 'failed';
      fileStatuses[i].error = err.message?.substring(0, 40) || 'Error';
    }
    renderBatchUI();
  }

  progressFill.style.width = "100%";
  btnExtract.disabled = false;
  btnExtract.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="11" cy="11" r="8"></circle>
      <path d="m21 21-4.35-4.35"></path>
    </svg>
    Extract All
  `;

  const successCount = extractionResults.filter(r => r.success).length;
  const failedCount = extractionResults.filter(r => !r.success).length;

  if (successCount === selectedFiles.length) {
    showStatus("success", `Successfully extracted data from ${successCount} document${successCount > 1 ? 's' : ''}`);
  } else {
    showStatus("error", `Extracted ${successCount}/${selectedFiles.length} documents. ${failedCount} failed.`);
  }

  // Show retry button if any failed
  if (failedCount > 0 && isBatch && btnRetryFailed) {
    btnRetryFailed.classList.remove("hidden");
  }

  setTimeout(() => progressBar.classList.add("hidden"), 1000);
  renderResults();
  saveToHistory(extractionResults);
});

// Retry Failed handler
if (btnRetryFailed) {
  btnRetryFailed.addEventListener("click", async () => {
    const failedFiles = [];
    const failedIndices = [];
    extractionResults.forEach((r, i) => {
      if (!r.success) {
        failedFiles.push(selectedFiles[i]);
        failedIndices.push(i);
      }
    });

    if (failedFiles.length === 0) return;
    btnRetryFailed.disabled = true;
    btnRetryFailed.textContent = '\ud83d\udd04 Retrying...';
    showStatus("loading", `Retrying ${failedFiles.length} failed document${failedFiles.length > 1 ? 's' : ''}...`);

    for (let j = 0; j < failedFiles.length; j++) {
      const origIndex = failedIndices[j];
      try {
        const result = await extractDocument(failedFiles[j]);
        extractionResults[origIndex] = { file: failedFiles[j].name, success: true, data: result };
      } catch (err) {
        extractionResults[origIndex] = { file: failedFiles[j].name, success: false, error: err.message };
      }
    }

    const newSuccess = extractionResults.filter(r => r.success).length;
    showStatus(newSuccess === extractionResults.length ? "success" : "error",
      `Retry complete: ${newSuccess}/${extractionResults.length} successful`);
    renderResults();
    btnRetryFailed.disabled = false;
    btnRetryFailed.textContent = '\ud83d\udd04 Retry Failed';
    if (extractionResults.every(r => r.success)) btnRetryFailed.classList.add("hidden");
  });
}

async function extractDocument(file) {
  const form = new FormData();
  form.append("file", file);
  form.append("document_type", documentTypeSelect.value);
  form.append("client_id", "default");

  // Add rotation if it's an image file
  const rotation = parseInt(rotationSelect.value) || 0;
  if (rotation && /\.(jpg|jpeg|png|tiff|tif)$/i.test(file.name)) {
    form.append("rotation", rotation.toString());
  }

  const res = await fetch(`${API}/api/extract`, {
    method: "POST",
    body: form,
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Extraction failed");
  return data;
}

// Status Messages
function showStatus(type, message) {
  statusMessage.className = `status-message status-${type}`;
  statusMessage.innerHTML = `
    ${type === "loading" ? '<div class="spinner"></div>' : ''}
    ${type === "success" ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>' : ''}
    ${type === "error" ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>' : ''}
    <span>${message}</span>
  `;
  statusMessage.classList.remove("hidden");
}

function hideStatus() {
  statusMessage.classList.add("hidden");
}

// Render Results
function renderResults() {
  resultsCard.classList.remove("hidden");

  // Stats
  const successCount = extractionResults.filter(r => r.success).length;
  let totalLineItems = 0;
  extractionResults.forEach(r => {
    if (r.success) {
      const extraction = r.data.extractionResult || r.data.document || r.data;
      const lines = extraction.lineItems || extraction.lineItem || [];
      totalLineItems += lines.length;
    }
  });

  statsGrid.innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${selectedFiles.length}</div>
      <div class="stat-label">Documents Processed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${successCount}</div>
      <div class="stat-label">Successful</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${totalLineItems}</div>
      <div class="stat-label">Line Items Found</div>
    </div>
  `;

  // Results for each document
  resultsContainer.innerHTML = extractionResults.map((result, index) => {
    if (!result.success) {
      return `
        <div class="results-section">
          <h3 class="section-title" style="color: var(--accent-danger);">
            ❌ ${result.file} - Failed
          </h3>
          <p style="color: var(--text-muted);">${result.error}</p>
        </div>
      `;
    }



    // Try multiple paths to find the data - SAP Document AI returns nested structure
    const extraction = result.data.extraction || result.data.extractionResult || result.data.document || result.data;


    // SAP Document AI returns arrays of {name, value, rawValue, confidence} objects
    let headerArray = extraction.headerFields || extraction.header || [];
    let linesArray = extraction.lineItemFields || extraction.lineItems || extraction.lineItem || [];

    // Convert array format to object for display - preserve confidence!
    let header = {};
    if (Array.isArray(headerArray)) {
      headerArray.forEach(field => {
        if (field.name && (field.value !== undefined || field.rawValue !== undefined)) {
          header[field.name] = {
            value: field.value !== undefined ? field.value : field.rawValue,
            confidence: field.confidence || 0
          };
        }
      });
    } else if (typeof headerArray === 'object') {
      header = headerArray;
    }

    // Handle line items - preserve confidence for each field
    let lines = [];
    if (Array.isArray(linesArray)) {
      // Check if it's array of line item rows (each row is array of fields)
      if (linesArray.length > 0 && Array.isArray(linesArray[0])) {
        lines = linesArray.map(row => {
          const lineObj = {};
          row.forEach(field => {
            if (field.name) {
              lineObj[field.name] = {
                value: field.value !== undefined ? field.value : field.rawValue,
                confidence: field.confidence || 0
              };
            }
          });
          return lineObj;
        });
      } else {
        lines = linesArray;
      }
    }

    // Count actual fields
    const headerCount = Object.keys(header).length;
    const hasData = headerCount > 0 || lines.length > 0;

    // If no structured data, show raw response
    if (!hasData) {
      return `
        <div class="results-section">
          <h3 class="section-title" style="color: var(--accent-warning);">
            ⚠️ ${result.file} - No structured data found
          </h3>
          <p style="color: var(--text-muted); margin-bottom: 1rem;">
            The document may not be a supported invoice format. SAP Document AI works best with standard invoices.
          </p>
          <details style="margin-top: 1rem;">
            <summary style="cursor: pointer; color: var(--text-secondary);">View raw API response</summary>
            <pre style="background: var(--bg-secondary); padding: 1rem; border-radius: 8px; overflow: auto; font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">${JSON.stringify(result.data, null, 2)}</pre>
          </details>
        </div>
      `;
    }

    return `
      <div class="results-section">
        <h3 class="section-title">📄 ${result.file}</h3>
        
        <h4 style="color: var(--text-secondary); margin: 1rem 0 0.5rem;">Header Fields (${headerCount})</h4>
        <div class="header-fields">
          ${Object.entries(header).map(([key, obj]) => {
      const value = obj && typeof obj === "object" && "value" in obj ? obj.value : obj;
      const confidence = obj && typeof obj === "object" && "confidence" in obj ? obj.confidence : null;
      const confPct = confidence !== null ? Math.round(confidence * 100) : null;
      const confClass = confPct === null ? 'confidence-none' : confPct >= 80 ? 'confidence-high' : confPct >= 50 ? 'confidence-medium' : 'confidence-low';
      const fieldClass = confPct !== null && confPct < 50 ? 'field-item low-confidence' : 'field-item';
      return `
              <div class="${fieldClass}">
                <div class="field-label">${key}${confPct !== null ? `<span class="confidence-badge ${confClass}" title="Confidence: ${confPct}%">${confPct}%</span>` : ''}</div>
                <div class="field-value">${formatValue(value)}</div>
              </div>
            `;
    }).join("")}
        </div>

        ${lines.length > 0 ? `
          <h4 style="color: var(--text-secondary); margin: 1rem 0 0.5rem;">Line Items (${lines.length})</h4>
          <table class="data-table">
            <thead>
              <tr>
                <th>Description</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Net Amount</th>
                <th>Conf.</th>
              </tr>
            </thead>
            <tbody>
              ${lines.map(item => {
      const desc = item.description?.value ?? item.description;
      const qty = item.quantity?.value ?? item.quantity;
      const unitP = item.unitPrice?.value ?? item.unitPrice;
      const netA = item.netAmount?.value ?? item.netAmount;
      // Average confidence across available fields
      const confs = [item.description?.confidence, item.quantity?.confidence, item.unitPrice?.confidence, item.netAmount?.confidence].filter(c => c !== undefined);
      const avgConf = confs.length > 0 ? Math.round((confs.reduce((a, b) => a + b, 0) / confs.length) * 100) : null;
      const confClass = avgConf === null ? 'confidence-none' : avgConf >= 80 ? 'confidence-high' : avgConf >= 50 ? 'confidence-medium' : 'confidence-low';
      return `
                <tr>
                  <td>${formatValue(desc)}</td>
                  <td>${formatValue(qty)}</td>
                  <td>${formatValue(unitP)}</td>
                  <td>${formatValue(netA)}</td>
                  <td><span class="confidence-badge ${confClass}" title="Avg confidence: ${avgConf}%">${avgConf !== null ? avgConf + '%' : '—'}</span></td>
                </tr>
              `}).join("")}
            </tbody>
          </table>
        ` : '<p style="color: var(--text-muted);">No line items found</p>'}
      </div>
    `;
  }).join("");
}

function formatValue(val) {
  if (val == null) return "—";
  if (typeof val === "object") return JSON.stringify(val);
  // Format numbers with 3 decimal places for amounts
  if (typeof val === "number") return val.toFixed(3);
  return String(val);
}

// Excel Export
btnExportExcel.addEventListener("click", () => {
  if (extractionResults.length === 0) return;

  // Create CSV content
  let csv = "File,Field,Value\n";

  extractionResults.forEach(result => {
    if (!result.success) return;

    const extraction = result.data.extraction || result.data.extractionResult || result.data.document || result.data;
    const headerArray = extraction.headerFields || extraction.header || [];

    // Handle array format from SAP API
    if (Array.isArray(headerArray)) {
      headerArray.forEach(field => {
        if (field.name && (field.value !== undefined || field.rawValue !== undefined)) {
          const value = field.value !== undefined ? field.value : field.rawValue;
          csv += `"${result.file}","${field.name}","${formatValue(value).replace(/"/g, '""')}"\n`;
        }
      });
    } else {
      Object.entries(headerArray).forEach(([key, obj]) => {
        const value = obj && typeof obj === "object" && "value" in obj ? obj.value : obj;
        csv += `"${result.file}","${key}","${formatValue(value).replace(/"/g, '""')}"\n`;
      });
    }
  });

  // Line items sheet
  csv += "\n\nLine Items\n";
  csv += "File,Description,Quantity,Unit Price,Net Amount\n";

  extractionResults.forEach(result => {
    if (!result.success) return;

    const extraction = result.data.extraction || result.data.extractionResult || result.data.document || result.data;
    const linesArray = extraction.lineItems || extraction.lineItem || [];

    // Handle array of arrays format from SAP API
    linesArray.forEach(lineRow => {
      let desc = "", qty = "", unit = "", net = "";

      if (Array.isArray(lineRow)) {
        // Each row is array of field objects
        lineRow.forEach(field => {
          if (field.name === "description") desc = field.value || field.rawValue || "";
          if (field.name === "quantity") qty = field.value || field.rawValue || "";
          if (field.name === "unitPrice") unit = field.value || field.rawValue || "";
          if (field.name === "netAmount") net = field.value || field.rawValue || "";
        });
      } else {
        // Object format
        desc = formatValue(lineRow.description?.value ?? lineRow.description);
        qty = formatValue(lineRow.quantity?.value ?? lineRow.quantity);
        unit = formatValue(lineRow.unitPrice?.value ?? lineRow.unitPrice);
        net = formatValue(lineRow.netAmount?.value ?? lineRow.netAmount);
      }

      csv += `"${result.file}","${String(desc).replace(/"/g, '""')}","${qty}","${unit}","${net}"\n`;
    });
  });

  // Download
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `document-ai-export-${new Date().toISOString().split('T')[0]}.csv`;
  link.click();
});

// =========================================
// HISTORY MANAGEMENT
// =========================================

function saveToHistory(results) {
  const historyEntry = {
    id: Date.now(),
    timestamp: new Date().toISOString(),
    files: results.map(r => r.file),
    successCount: results.filter(r => r.success).length,
    totalCount: results.length,
    // Store summary data, not full response (to save space)
    summary: results.filter(r => r.success).map(r => {
      const extraction = r.data.extraction || r.data.extractionResult || r.data;
      const headerFields = extraction.headerFields || [];
      const lineItems = extraction.lineItems || [];
      return {
        file: r.file,
        headerCount: headerFields.length,
        lineItemCount: lineItems.length,
        grossAmount: headerFields.find(f => f.name === "grossAmount")?.value,
        documentNumber: headerFields.find(f => f.name === "documentNumber")?.value
      };
    })
  };

  processingHistory.unshift(historyEntry);
  // Keep only last 20 entries
  if (processingHistory.length > 20) {
    processingHistory = processingHistory.slice(0, 20);
  }
  localStorage.setItem(HISTORY_KEY, JSON.stringify(processingHistory));
  renderHistory();
}

function renderHistory() {
  if (processingHistory.length === 0) {
    historyContainer.innerHTML = '<p style="color: var(--text-muted); padding: 1rem;">No processing history yet.</p>';
    return;
  }

  historyContainer.innerHTML = processingHistory.map(entry => {
    const date = new Date(entry.timestamp);
    const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return `
      <div class="history-item" style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color);">
        <div>
          <div style="font-weight: 500; color: var(--text-primary);">${entry.files.join(", ")}</div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">
            ${dateStr} • ${entry.successCount}/${entry.totalCount} successful
            ${entry.summary.length > 0 && entry.summary[0].documentNumber ? ` • ${entry.summary[0].documentNumber}` : ''}
            ${entry.summary.length > 0 && entry.summary[0].grossAmount ? ` • ${formatValue(entry.summary[0].grossAmount)}` : ''}
          </div>
        </div>
        <span style="background: ${entry.successCount === entry.totalCount ? '#22c55e' : '#eab308'}; color: white; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px;">
          ${entry.summary.reduce((sum, s) => sum + s.lineItemCount, 0)} items
        </span>
      </div>
    `;
  }).join("");
}

// Clear History
btnClearHistory.addEventListener("click", () => {
  if (confirm("Clear all processing history?")) {
    processingHistory = [];
    localStorage.setItem(HISTORY_KEY, "[]");
    renderHistory();
  }
});

// Initialize history on page load
renderHistory();
