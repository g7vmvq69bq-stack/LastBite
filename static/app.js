/**
 * app.js
 * ------
 * Frontend logic for LastBite.
 *
 * Handles all user interactions in the single-page app:
 *   - Tab switching (Scan, Pantry, Survival, Recipes)
 *   - Image upload and food scanning
 *   - Pantry display and manual item management
 *   - Survival runway display
 *   - Recipe suggestions display
 *   - Demo data loading
 *
 * Communicates with the FastAPI backend via fetch() calls.
 */

'use strict';

// Global state — items detected from the last scan, and the uploaded file
let detectedItems = [];
let currentFile   = null;


// ── Tab navigation ─────────────────────────────────────────────────────────────
// When a tab button is clicked, hide all tabs and show the selected one.
// Also trigger a data reload for the relevant tab.

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.tab;

    // Deactivate all tab buttons and hide all tab panels
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => { t.hidden = true; });

    // Activate the clicked tab
    btn.classList.add('active');
    document.getElementById(`tab-${id}`).hidden = false;

    // Load fresh data from the server when switching tabs
    if (id === 'pantry')   loadPantry();
    if (id === 'survival') loadRunway();
    if (id === 'recipes')  loadRecipes();
  });
});


// ── Image upload and scanning ──────────────────────────────────────────────────

// When the user selects an image file, show a preview
document.getElementById('fileInput').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;

  currentFile = file;
  document.getElementById('previewImg').src = URL.createObjectURL(file);
  document.getElementById('uploadPlaceholder').hidden = true;
  document.getElementById('imagePreview').hidden = false;
  document.getElementById('scanResults').hidden  = true;
});

/** Clear the current image and reset the scan area. */
function clearImage() {
  currentFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('uploadPlaceholder').hidden = false;
  document.getElementById('imagePreview').hidden = true;
  document.getElementById('scanResults').hidden  = true;
}

/**
 * Send the selected image to the backend for AI scanning.
 * The backend uses GPT-4o Vision to detect food items and quantities.
 */
async function scanImage() {
  if (!currentFile) return;

  // Show loading spinner while waiting for the AI response
  document.getElementById('imagePreview').hidden = true;
  document.getElementById('scanLoading').hidden  = false;
  document.getElementById('scanResults').hidden  = true;

  try {
    // Send image as multipart form data to /api/scan
    const fd = new FormData();
    fd.append('file', currentFile);
    const res  = await fetch('/api/scan', { method: 'POST', body: fd });
    const data = await res.json();

    // Store detected items and render them on screen
    detectedItems = data.detected || [];
    renderDetected();
  } catch {
    alert('Error scanning image – please try again.');
    document.getElementById('imagePreview').hidden = false;
  } finally {
    document.getElementById('scanLoading').hidden = true;
  }
}

/**
 * Render the detected food items as editable cards.
 * The user can adjust quantities or remove incorrect items
 * before adding them to the pantry.
 */
function renderDetected() {
  const grid = document.getElementById('detectedGrid');

  if (!detectedItems.length) {
    grid.innerHTML = '<p style="color:var(--muted);font-size:14px">No food items detected. Try a clearer photo.</p>';
  } else {
    grid.innerHTML = detectedItems.map((item, idx) => `
      <div class="detected-item">
        <button class="di-remove" onclick="removeDetected(${idx})" title="Remove">×</button>
        <div class="di-name">${esc(item.name)}</div>
        <div class="di-qty">qty:
          <input class="qty-input" type="number" min="1" max="99" value="${esc(item.quantity || '1')}"
            onchange="detectedItems[${idx}].quantity = this.value" />
        </div>
        <div class="di-cat">${esc(item.category || 'other')}</div>
      </div>
    `).join('');
  }

  // Enable the "Add All" button
  const addBtn = document.getElementById('addAllBtn');
  addBtn.disabled = false;
  addBtn.textContent = '✓ Add All to Pantry';
  addBtn.className = 'btn success';
  document.getElementById('scanResults').hidden = false;
}

/** Remove one incorrectly detected item from the results list. */
function removeDetected(idx) {
  detectedItems.splice(idx, 1);
  renderDetected();
}

/**
 * Send all confirmed detected items to the pantry in one bulk request.
 * Automatically switches to the Pantry tab when done.
 */
async function addAllToPantry() {
  if (!detectedItems.length) return;

  const btn = document.getElementById('addAllBtn');
  btn.disabled = true;
  btn.textContent = 'Adding…';

  try {
    const res  = await fetch('/api/pantry/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(detectedItems.map(i => ({
        name: i.name, quantity: i.quantity || '1', category: i.category || 'other',
      }))),
    });
    const data = await res.json();
    btn.textContent = `✓ Added ${data.added.length} items!`;

    // Switch to pantry tab after a short delay so the user sees the confirmation
    setTimeout(() => {
      clearImage();
      resetScanUI();  // Only reset the scan UI, do NOT clear the pantry
      document.querySelector('[data-tab="pantry"]').click();
    }, 1400);
  } catch {
    alert('Error adding items.');
    btn.disabled = false;
    btn.textContent = '✓ Add All to Pantry';
  }
}

/** Reset only the scan UI — does NOT touch the pantry database. */
function resetScanUI() {
  detectedItems = [];
  document.getElementById('scanResults').hidden  = true;
  document.getElementById('imagePreview').hidden = false;
}

/**
 * Reset the scan UI AND clear all pantry data.
 * Called when the user clicks "Scan Again" to start completely fresh.
 * Survival and Recipes tabs will show empty until new items are scanned.
 */
async function clearScan() {
  resetScanUI();

  // Clear the pantry database
  await fetch('/api/pantry', { method: 'DELETE' });

  // Reset survival tab to empty
  document.getElementById('runwayDays').textContent = '--';
  document.getElementById('statMeals').textContent  = '--';
  document.getElementById('statItems').textContent  = '--';
  document.getElementById('criticalBox').hidden = true;
  document.getElementById('breakdownList').innerHTML = '<p style="color:var(--muted);font-size:14px">No items yet.</p>';

  // Reset recipes tab to empty
  document.getElementById('recipesList').innerHTML = '<div class="empty-state"><p>No recipes yet – add ingredients to your pantry first.</p></div>';

  // Reset pantry tab to empty
  document.getElementById('pantryList').innerHTML = '<div class="empty-state"><p>Your pantry is empty – scan some food to get started!</p></div>';
}


// ── Pantry ─────────────────────────────────────────────────────────────────────

/** Fetch all pantry items from the server and display them. */
async function loadPantry() {
  const res  = await fetch('/api/pantry');
  const data = await res.json();
  renderPantry(data.items || []);
}

/**
 * Render pantry items as coloured cards.
 * Each card shows the item name, days remaining, category, and quantity.
 * Colour coding: green = fresh, orange = expiring soon, red = expired.
 */
function renderPantry(items) {
  const list = document.getElementById('pantryList');

  if (!items.length) {
    list.innerHTML = '<div class="empty-state"><p>Your pantry is empty – scan some food to get started!</p></div>';
    return;
  }

  list.innerHTML = items.map(item => {
    const daysLabel = item.days_remaining > 0
      ? `${item.days_remaining}d left`
      : 'Expired';

    return `
      <div class="pantry-item ${esc(item.status)}">
        <div class="pi-info">
          <div class="pi-name">${esc(item.name)}</div>
          <div class="pi-meta">
            <span class="badge ${esc(item.status)}">${daysLabel}</span>
            <span class="badge cat">${esc(item.category)}</span>
            <span class="badge qty">× ${esc(item.quantity)}</span>
          </div>
        </div>
        <button class="del-btn" onclick="deleteItem(${item.id})" title="Remove">×</button>
      </div>
    `;
  }).join('');
}

/** Show or hide the manual item entry form. */
function toggleAddForm() {
  const f = document.getElementById('addForm');
  f.hidden = !f.hidden;
  if (!f.hidden) document.getElementById('fName').focus();
}

/** Submit a manually entered item to the pantry. */
async function addManual() {
  const name = document.getElementById('fName').value.trim();
  const qty  = document.getElementById('fQty').value.trim() || '1';
  const cat  = document.getElementById('fCat').value;

  if (!name) { alert('Please enter a food name.'); return; }

  await fetch('/api/pantry', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, quantity: qty, category: cat }),
  });

  // Reset form fields and reload pantry
  document.getElementById('fName').value = '';
  document.getElementById('fQty').value  = '1';
  document.getElementById('addForm').hidden = true;
  loadPantry();
}

/** Delete a pantry item by its database ID. */
async function deleteItem(id) {
  await fetch(`/api/pantry/${id}`, { method: 'DELETE' });
  loadPantry();
}

/** Clear all items from the pantry. */
async function clearPantry() {
  await fetch('/api/pantry', { method: 'DELETE' });
  document.getElementById('pantryList').innerHTML =
    '<div class="empty-state"><p>Your pantry is empty – scan some food to get started!</p></div>';
}


// ── Survival Runway ────────────────────────────────────────────────────────────

/**
 * Fetch the survival runway data and update the dashboard.
 * Shows total survival days, meal count, critical items, and per-item breakdown.
 */
async function loadRunway() {
  const res  = await fetch('/api/runway');
  const data = await res.json();

  // Update the main stats
  document.getElementById('runwayDays').textContent = data.survival_days ?? '--';
  document.getElementById('statMeals').textContent  = data.total_meals   ?? '--';
  document.getElementById('statItems').textContent  = data.item_count    ?? '--';

  // Show critical items (expiring within 3 days) if any exist
  const critBox  = document.getElementById('criticalBox');
  const critList = document.getElementById('criticalList');
  const crits    = data.critical_items || [];

  if (crits.length) {
    critBox.hidden = false;
    critList.innerHTML = crits.map(i => `
      <div class="crit-item">
        <span style="text-transform:capitalize">${esc(i.name)}</span>
        <span class="crit-days">${i.days_remaining}d left</span>
      </div>
    `).join('');
  } else {
    critBox.hidden = true;
  }

  // Show the meal contribution breakdown per item
  const bd        = document.getElementById('breakdownList');
  const breakdown = data.breakdown || [];

  if (breakdown.length) {
    bd.innerHTML = breakdown.map(i => `
      <div class="bd-item">
        <span style="text-transform:capitalize">${esc(i.name)}</span>
        <span class="bd-meals">${i.meals} meals</span>
      </div>
    `).join('');
  } else {
    bd.innerHTML = '<p style="color:var(--muted);font-size:14px">No items yet.</p>';
  }
}


// ── Recipes ────────────────────────────────────────────────────────────────────

/** Fetch recipe suggestions from the server and display them. */
async function loadRecipes() {
  const list = document.getElementById('recipesList');
  list.innerHTML = '';
  document.getElementById('recipesLoading').hidden = false;

  try {
    const res  = await fetch('/api/recipes');
    const data = await res.json();
    renderRecipes(data.recipes || []);
  } catch {
    list.innerHTML = '<p style="color:var(--danger)">Error loading recipes.</p>';
  } finally {
    document.getElementById('recipesLoading').hidden = true;
  }
}

/**
 * Render recipe suggestion cards.
 * Each card shows the recipe name, cook time, description, ingredient tags,
 * and step-by-step cooking instructions.
 */
function renderRecipes(recipes) {
  const list = document.getElementById('recipesList');

  if (!recipes.length) {
    list.innerHTML = '<div class="empty-state"><p>No recipes yet – add ingredients to your pantry first.</p></div>';
    return;
  }

  list.innerHTML = recipes.map(r => `
    <div class="recipe-card">
      <div class="recipe-header">
        <div class="recipe-name">${esc(r.name)}</div>
        <div class="recipe-time">⏱ ${r.time_minutes ?? '?'} min</div>
      </div>
      <div class="recipe-desc">${esc(r.description || '')}</div>
      ${r.priority_reason ? `<div class="recipe-priority">⚠️ ${esc(r.priority_reason)}</div>` : ''}
      <div class="sub-title">Uses</div>
      <div class="ing-tags">
        ${(r.ingredients_used || []).map(i => `<span class="ing-tag">${esc(i)}</span>`).join('')}
      </div>
      <div class="sub-title">Steps</div>
      <ol class="steps-list">
        ${(r.steps || []).map(s => `<li>${esc(s)}</li>`).join('')}
      </ol>
    </div>
  `).join('');
}



// ── Utility ────────────────────────────────────────────────────────────────────

/**
 * Safely escape a string for insertion into HTML.
 * Prevents XSS attacks by converting special characters to HTML entities.
 */
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}


// ── Startup ────────────────────────────────────────────────────────────────────
// Load the pantry when the page first opens
loadPantry();
