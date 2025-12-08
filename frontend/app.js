// --- CONFIGURATION ---
const BASE_URL = "http://localhost:8000";
const ENDPOINTS = {
    // OCR: upload image/pdf as 'file'
    ocrExtract: `${BASE_URL}/api/v1/ocr/extract-text`,
    // Mapping + Verification using extracted raw text
    map: `${BASE_URL}/api/v1/map-and-verify`,
    // Optional submit endpoint (may not exist; fallback provided)
    submit: `${BASE_URL}/api/v1/submit`
};

// --- DOM ELEMENTS ---
const views = {
    dashboard: document.getElementById('view-dashboard'),
    form: document.getElementById('view-form'),
    upload: document.getElementById('view-upload'),
    verify: document.getElementById('view-verify'),
    success: document.getElementById('view-success'),
    review: document.getElementById('view-review')
};

// Specific verification document inputs (any of these triggers OCR)
const aadharFileEl = document.getElementById('aadharFile');
const passportFileEl = document.getElementById('passportFile');
const birthCertFileEl = document.getElementById('birthCertFile');
// Applicant form fields
const firstNameEl = document.getElementById('firstName');
const middleNameEl = document.getElementById('middleName');
const lastNameEl = document.getElementById('lastName');
const dobEl = document.getElementById('dob');
const genderEl = document.getElementById('gender');
const addressEl = document.getElementById('address');
const emailEl = document.getElementById('email');
const phoneEl = document.getElementById('phone');

// Editable review inputs on upload page
const editNameEl = document.getElementById('edit-name');
const editDobEl = document.getElementById('edit-dob');
const editGenderEl = document.getElementById('edit-gender');
const editAddressEl = document.getElementById('edit-address');
const editEmailEl = document.getElementById('edit-email');
const editPhoneEl = document.getElementById('edit-phone');
const loadingSpinner = document.getElementById('loading-spinner');
const verifyForm = document.getElementById('verify-form');
const previewImg = document.getElementById('preview-img');
// No dedicated upload zone after UI change
// Review page elements
const docListEl = document.getElementById('doc-list');
const confidencePanelEl = document.getElementById('confidence-panel');
const finalSubmitBtn = document.getElementById('final-submit');
const extractedBoxEl = document.getElementById('extracted-box');
const extractedTitleEl = document.getElementById('extracted-title');
const extractedConfidenceEl = document.getElementById('extracted-confidence');
const extractedTextEl = document.getElementById('extracted-text');
const extractedTextInputEl = document.getElementById('extracted-text-input');
const editExtractedBtn = document.getElementById('edit-extracted');
const saveExtractedBtn = document.getElementById('save-extracted');
// Edit/Save controls
const editBtn = document.getElementById('edit-applicant');
const saveBtn = document.getElementById('save-applicant');
const handwrittenFileEl = document.getElementById('handwrittenFile');

let currentObjectUrl = null; // Track image memory for privacy cleanup
const selectedDocs = { name: null, address: null, dob: null };
let reviewResults = null; // Persist results for finalize download
let isEditingApplicant = false;
let currentDocKey = null;
let originalExtractedText = '';
let isEditingExtracted = false;

function switchView(viewName) {
    Object.values(views).forEach(el => el.classList.add('d-none'));
    const key = viewName.replace('view-', '');
    views[key].classList.remove('d-none');
}
// Expose for inline onclick handlers
window.switchView = switchView;
// Attach handler to Start button (dashboard -> form)
document.getElementById('start-registration')?.addEventListener('click', () => switchView('view-form'));
// Handle form submission to move to upload step
const continueBtn = document.getElementById('continue-to-upload');
continueBtn?.addEventListener('click', () => {
        const form = document.getElementById('applicant-form');
    if (form && !form.checkValidity()) {
        form.reportValidity();
        return;
    }
    // Proceed to upload page
    switchView('view-upload');

    // Populate editable review inputs on upload page
    const fullName = [firstNameEl?.value, middleNameEl?.value, lastNameEl?.value]
        .filter(Boolean)
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();
    if (editNameEl) editNameEl.value = fullName || '';
    if (editDobEl) editDobEl.value = dobEl?.value || '';
    if (editGenderEl) editGenderEl.value = genderEl?.value || '';
    if (editAddressEl) editAddressEl.value = addressEl?.value || '';
    if (editEmailEl) editEmailEl.value = emailEl?.value || '';
    if (editPhoneEl) editPhoneEl.value = phoneEl?.value || '';
});

// Helper to build user object from either original form or editable review inputs
function buildUserFromUI() {
    const nameFromReview = editNameEl?.value?.trim();
    const dobFromReview = editDobEl?.value || '';
    const genderFromReview = editGenderEl?.value || '';
    const addressFromReview = editAddressEl?.value || '';
    const emailFromReview = editEmailEl?.value || '';
    const phoneFromReview = editPhoneEl?.value || '';

    const nameFromForm = [firstNameEl?.value, middleNameEl?.value, lastNameEl?.value]
        .filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();

    return {
        name: nameFromReview || nameFromForm || '',
        dob: dobFromReview || dobEl?.value || '',
        gender: genderFromReview || genderEl?.value || '',
        address: addressFromReview || addressEl?.value || '',
        email: emailFromReview || emailEl?.value || '',
        phone: phoneFromReview || phoneEl?.value || ''
    };
}

// --- MAIN UPLOAD LOGIC (supports any of the three inputs) ---
async function handleSelectedFile(file) {
    if (!file) return;

    // 1. PRIVACY CLEANUP: Revoke old image memory
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);

    currentObjectUrl = URL.createObjectURL(file);
    previewImg.src = currentObjectUrl;
    if (previewImg.classList.contains('d-none')) previewImg.classList.remove('d-none');

    loadingSpinner.classList.remove('d-none');

    const formData = new FormData();
    formData.append('file', file);

    try {
        console.log('🚀 Step 1: Sending to OCR extraction...');
        const ocrRes = await fetch(ENDPOINTS.ocrExtract, { method: 'POST', body: formData });
        if (!ocrRes.ok) throw new Error(`OCR Extraction Failed: ${ocrRes.status}`);

        const ocrJson = await ocrRes.json();
        const rawText = ocrJson.extracted_text || ocrJson.raw_text || ocrJson.data?.raw_text || '';

        const user = buildUserFromUI();
        console.log('🚀 Step 2: Sending to Mapping & Verification...');
        const mapRes = await fetch(ENDPOINTS.map, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: rawText, user })
        });
        if (!mapRes.ok) throw new Error(`Mapping Failed: ${mapRes.status}`);

        const mapJson = await mapRes.json();
        // Keep user on the upload page; do not switch views here.
        // We only run per-document OCR/mapping and navigate on Confirm & Submit.
    } catch (err) {
        console.error(err);
        alert(`Error: ${err.message}. Is Backend running on port 8000?`);
    } finally {
        loadingSpinner.classList.add('d-none');
    }
}

[aadharFileEl, passportFileEl, birthCertFileEl].forEach((el) => {
    if (!el) return;
    el.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (el === aadharFileEl) selectedDocs.name = file;
        if (el === passportFileEl) selectedDocs.address = file;
        if (el === birthCertFileEl) selectedDocs.dob = file;
    });
});

// Optional handwritten doc tracking
handwrittenFileEl?.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    // We won't process this unless present; treat as supplemental (no mapping changes here)
    if (file) {
        console.log('Optional handwritten doc selected:', file.name);
    }
});

// Toggle editable state for preview inputs
editBtn?.addEventListener('click', () => {
    isEditingApplicant = true;
    [editNameEl, editDobEl, editGenderEl, editAddressEl, editEmailEl, editPhoneEl].forEach(el => el && (el.disabled = false));
    // Show bottom Save button when editing
    const saveBtnEl = document.getElementById('save-applicant');
    if (saveBtnEl) saveBtnEl.classList.remove('d-none');
});

saveBtn?.addEventListener('click', () => {
    isEditingApplicant = false;
    [editNameEl, editDobEl, editGenderEl, editAddressEl, editEmailEl, editPhoneEl].forEach(el => el && (el.disabled = true));
    // Hide bottom Save button when not editing
    const saveBtnEl = document.getElementById('save-applicant');
    if (saveBtnEl) saveBtnEl.classList.add('d-none');
});

// --- RENDER FORM (Updated for Team A's Test Structure) ---
function renderForm(data) {
    verifyForm.innerHTML = '';
    
    // 1. CHECK FOR VERIFICATION NOTES (The "Age Mismatch" Bonus)
    // The test shows: data.verification.notes = ["age_mismatch..."]
    if (data.verification && data.verification.notes && data.verification.notes.length > 0) {
        const warnings = data.verification.notes.join("<br>");
        const warningHtml = `
            <div class="alert alert-warning d-flex align-items-center mb-3" role="alert">
                <span class="me-2 fs-4">⚠️</span>
                <div>
                    <strong>Verification Warning:</strong><br>
                    ${warnings}
                </div>
            </div>
        `;
        verifyForm.insertAdjacentHTML('beforeend', warningHtml);
    }

    // 2. NORMALIZE THE DATA STRUCTURE
    // The test uses "mapped", but we keep support for others just in case
    if (data.mapped) {
        data = data.mapped;
    } else if (data.verification && data.verification.mapped_fields) {
        data = data.verification.mapped_fields;
    } else if (data.data) {
        data = data.data;
    }

    // 3. GENERATE FIELDS
    for (const [key, field] of Object.entries(data)) {
        // Handle value/confidence objects OR simple strings
        const val = field.value || field || "";
        // If confidence is missing, assume 1.0 (High)
        const conf = (field.confidence !== undefined) ? field.confidence : 1.0;
        
        const isLowConf = conf < 0.6;
        const borderClass = isLowConf ? 'border-warning bg-warning bg-opacity-10' : 'border-success';
        
        const html = `
            <div class="mb-3">
                <label class="form-label text-uppercase small fw-bold text-secondary">${key}</label>
                <div class="input-group">
                    <input type="text" data-key="${key}" class="form-control ${borderClass}" value="${val}">
                    <span class="input-group-text ${isLowConf ? 'bg-warning' : 'bg-success text-white'}">
                        ${isLowConf ? '⚠️' : '✓'}
                    </span>
                </div>
                ${isLowConf ? `<small class="text-warning fw-bold">Low Confidence (${(conf*100).toFixed(0)}%) - Check Original</small>` : ''}
            </div>
        `;
        verifyForm.insertAdjacentHTML('beforeend', html);
    }
}

// --- SUBMIT DATA (Privacy & Fallback Version) ---
async function submitData() {
    // Process selected documents and render the review page with confidence scores
    const user = buildUserFromUI();
    const results = {};

    const processDoc = async (key, file) => {
        const fd = new FormData();
        fd.append('file', file);
        const ocrRes = await fetch(ENDPOINTS.ocrExtract, { method: 'POST', body: fd });
        if (!ocrRes.ok) throw new Error(`OCR failed for ${key}: ${ocrRes.status}`);
        const ocrJson = await ocrRes.json();
        const rawText = ocrJson.extracted_text || ocrJson.raw_text || ocrJson.data?.raw_text || '';
        // Map key to backend document_type for focused verification
        const docTypeMap = { name: 'aadhar', address: 'dl', dob: 'birth', handwritten: null };
        const document_type = docTypeMap[key] || null;

        const mapRes = await fetch(ENDPOINTS.map, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: rawText, user, document_type })
        });
        if (!mapRes.ok) throw new Error(`Map failed for ${key}: ${mapRes.status}`);
        const mapJson = await mapRes.json();
        // Prefer structured mapped fields
        const fields = mapJson.mapped || mapJson.mapped_fields || mapJson.data || mapJson;
        // Extract verification info if available
        const verification = mapJson.verification || null;
        const url = URL.createObjectURL(file);
        results[key] = { fileName: file.name, rawText, fields, verification, url };
    };

    const tasks = [];
    if (selectedDocs.name) tasks.push(processDoc('name', selectedDocs.name));
    if (selectedDocs.address) tasks.push(processDoc('address', selectedDocs.address));
    if (selectedDocs.dob) tasks.push(processDoc('dob', selectedDocs.dob));
    // Include optional handwritten document (extract all fields)
    const handwritten = handwrittenFileEl && handwrittenFileEl.files && handwrittenFileEl.files[0];
    if (handwritten) tasks.push(processDoc('handwritten', handwritten));

    if (tasks.length === 0) {
        alert('Please upload at least one document before submitting.');
        return;
    }

    loadingSpinner.classList.remove('d-none');
    try {
        await Promise.all(tasks);
    } catch (e) {
        console.error(e);
        alert(`Error during document processing: ${e.message}`);
    } finally {
        loadingSpinner.classList.add('d-none');
    }

    try {
        // Switch first so the review elements are visible in DOM
        switchView('view-review');
        renderReview(results);
        reviewResults = results;
    } catch (e) {
        console.error('Render error:', e);
        alert('Unable to render review page. Please check console logs.');
    }
}

function renderReview(results) {
    console.log('Rendering review with results:', results);
    // Left list with view buttons
    if (!docListEl || !confidencePanelEl || !extractedBoxEl || !extractedTitleEl || !extractedConfidenceEl || !extractedTextEl) {
        throw new Error('Review page elements not found');
    }
    docListEl.innerHTML = '';
    const order = [
        { key: 'name', label: 'Aadhaar/Voter ID (Name)' },
        { key: 'address', label: 'DL/Passport (Address)' },
        { key: 'dob', label: 'Birth/SLC (DOB)' },
        { key: 'handwritten', label: 'Handwritten (All Fields)' }
    ];
    order.forEach(({ key, label }) => {
        const item = results[key];
        if (!item) return;
        const html = `
            <div class="list-group-item mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="fw-semibold">${label}</div>
                        <div class="text-muted small">${item.fileName}</div>
                    </div>
                    <div class="btn-group">
                        <button class="btn btn-outline-secondary btn-sm" data-action="view-doc" data-key="${key}">View Document</button>
                        <button class="btn btn-outline-secondary btn-sm" data-action="view-text" data-key="${key}">View Extracted Text</button>
                    </div>
                </div>
            </div>
        `;
        docListEl.insertAdjacentHTML('beforeend', html);
    });

    docListEl.onclick = (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const key = btn.getAttribute('data-key');
        const item = results[key];
        if (!item) return;
        if (btn.getAttribute('data-action') === 'view-doc') {
            if (item.url) {
                try { window.open(item.url, '_blank'); }
                catch(err) { console.error('Open doc failed:', err); }
            }
        } else {
            // Populate right panel with MAPPED data and verification score
            const fields = item.fields || {};
            const verification = item.verification || {};
            // Build display text from mapped fields with per-doc filtering
            const lines = [];
            const filterKeys = key === 'name' ? ['name'] : key === 'address' ? ['address'] : key === 'dob' ? ['dob'] : null;
            Object.entries(fields).forEach(([k, v]) => {
                if (filterKeys && !filterKeys.includes(k)) return;
                const val = (v && typeof v === 'object' && 'value' in v) ? v.value : v;
                if (val !== undefined && val !== null && String(val).trim() !== '') {
                    lines.push(`${k}: ${val}`);
                }
            });
            // Only show mapped fields; avoid falling back to raw OCR text
            const displayText = lines.length ? lines.join('\n') : '(no text)';

            // Determine verification score if provided; fallback to avg confidence
            let scorePct = null;
            if (typeof verification?.score === 'number') {
                scorePct = Math.round(verification.score * 100);
            } else if (typeof verification?.overall_confidence === 'number') {
                scorePct = Math.round(verification.overall_confidence * 100);
            } else {
                let total = 0, count = 0;
                Object.values(fields).forEach(f => {
                    const conf = (f && typeof f === 'object' && f.confidence !== undefined) ? Number(f.confidence) : 1.0;
                    total += conf; count += 1;
                });
                const avg = count ? total / count : 0;
                scorePct = Math.round(avg * 100);
            }

            extractedTitleEl.textContent = item.fileName;
            extractedConfidenceEl.textContent = `${scorePct}%`;
            extractedConfidenceEl.className = `badge ${scorePct < 60 ? 'bg-warning text-dark' : 'bg-success'}`;
            extractedTextEl.textContent = displayText;
            if (extractedTextInputEl) {
                extractedTextInputEl.value = displayText;
                extractedTextInputEl.classList.add('d-none');
            }
            if (extractedTextEl) extractedTextEl.classList.remove('d-none');
            if (editExtractedBtn) editExtractedBtn.classList.remove('d-none');
            if (saveExtractedBtn) {
                saveExtractedBtn.classList.add('d-none');
                saveExtractedBtn.disabled = true;
            }
            currentDocKey = key;
            originalExtractedText = displayText;
            isEditingExtracted = false;
            extractedBoxEl.classList.remove('d-none');
        }
    };

    // Right confidence panel
    confidencePanelEl.innerHTML = '';
    Object.entries(results).forEach(([key, item]) => {
        const fields = item.fields || {};
        const verification = item.verification || {};
        let score = null;
        if (typeof verification?.score === 'number') {
            score = verification.score;
        } else if (typeof verification?.overall_confidence === 'number') {
            score = verification.overall_confidence;
        } else {
            let total = 0, count = 0;
            Object.values(fields).forEach(f => {
                const conf = (f && typeof f === 'object' && f.confidence !== undefined) ? Number(f.confidence) : 1.0;
                total += conf; count += 1;
            });
            score = count ? total / count : 0;
        }
        const label = key === 'name' ? 'Name Doc' : key === 'address' ? 'Address Doc' : key === 'dob' ? 'DOB Doc' : 'Handwritten Doc';
        const html = `
            <div class="mb-3">
                <div class="d-flex justify-content-between">
                    <span class="fw-semibold">${label}</span>
                    <span class="badge ${score < 0.6 ? 'bg-warning text-dark' : 'bg-success'}">${Math.round(score*100)}%</span>
                </div>
                <div class="small text-muted">Average confidence across extracted fields.</div>
            </div>
        `;
        confidencePanelEl.insertAdjacentHTML('beforeend', html);
    });
}

// --- INLINE EDITING FOR EXTRACTED TEXT ON REVIEW ---
editExtractedBtn?.addEventListener('click', () => {
    if (!currentDocKey || !extractedTextInputEl || !extractedTextEl) return;
    isEditingExtracted = true;
    extractedTextEl.classList.add('d-none');
    extractedTextInputEl.classList.remove('d-none');
    extractedTextInputEl.focus();
    originalExtractedText = extractedTextInputEl.value;
    if (editExtractedBtn) editExtractedBtn.classList.add('d-none');
    if (saveExtractedBtn) {
        saveExtractedBtn.classList.remove('d-none');
        saveExtractedBtn.disabled = true;
    }
});

extractedTextInputEl?.addEventListener('input', () => {
    if (!isEditingExtracted || !saveExtractedBtn || !extractedTextInputEl) return;
    const changed = extractedTextInputEl.value !== originalExtractedText;
    saveExtractedBtn.disabled = !changed;
});

saveExtractedBtn?.addEventListener('click', async () => {
    if (!currentDocKey || !extractedTextInputEl || !saveExtractedBtn) return;
    const newText = extractedTextInputEl.value;
    const changed = newText !== originalExtractedText;
    if (!changed) {
        // Nothing to save; just exit edit mode
        extractedTextInputEl.classList.add('d-none');
        if (extractedTextEl) extractedTextEl.classList.remove('d-none');
        if (saveExtractedBtn) saveExtractedBtn.classList.add('d-none');
        if (editExtractedBtn) editExtractedBtn.classList.remove('d-none');
        isEditingExtracted = false;
        return;
    }

    saveExtractedBtn.disabled = true;
    const prevLabel = saveExtractedBtn.textContent;
    saveExtractedBtn.textContent = 'Saving...';
    try {
        const user = buildUserFromUI();
        const docTypeMap = { name: 'aadhar', address: 'dl', dob: 'birth', handwritten: null };
        const document_type = docTypeMap[currentDocKey] || null;

        const mapRes = await fetch(ENDPOINTS.map, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: newText, user, document_type })
        });
        if (!mapRes.ok) throw new Error(`Update failed (${mapRes.status})`);
        const mapJson = await mapRes.json();
        const fields = mapJson.mapped || mapJson.mapped_fields || mapJson.data || mapJson;
        const verification = mapJson.verification || null;

        // Persist updated results for finalize and confidence panel
        reviewResults = reviewResults || {};
        reviewResults[currentDocKey] = {
            ...(reviewResults[currentDocKey] || {}),
            rawText: newText,
            fields,
            verification
        };

        // Re-render panels and reopen the same doc to reflect new confidence
        renderReview(reviewResults);
        const reopenBtn = docListEl?.querySelector(`button[data-action="view-text"][data-key="${currentDocKey}"]`);
        reopenBtn?.click();
    } catch (err) {
        console.error(err);
        alert(`Unable to save edits: ${err.message}`);
        saveExtractedBtn.disabled = false;
    } finally {
        saveExtractedBtn.textContent = prevLabel || 'Save';
    }
});

// Finalize: download JSON and return to first page
finalSubmitBtn?.addEventListener('click', () => {
    try {
        const payload = {
            user: buildUserFromUI(),
            documents: reviewResults || {},
            timestamp: new Date().toISOString()
        };
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(payload, null, 2));
        const a = document.createElement('a');
        a.setAttribute('href', dataStr);
        a.setAttribute('download', 'verification_review.json');
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        console.error('Finalize download failed:', err);
        alert('Failed to generate JSON. See console for details.');
    }
    // Navigate back to dashboard (first page)
    switchView('view-dashboard');
});

// No drag & drop after removing the upload zone