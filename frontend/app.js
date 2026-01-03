// --- CONFIGURATION ---
const BASE_URL = "http://localhost:8000";
const ENDPOINTS = {
    // OCR: upload image/pdf as 'file'
    ocrExtract: `${BASE_URL}/api/v1/ocr/extract-text`,
    // Mapping + Verification using extracted raw text
    map: `${BASE_URL}/api/v1/map-and-verify`,
    // Optional submit endpoint (may not exist; fallback provided)
    submit: `${BASE_URL}/api/v1/submit`,
    // MOSIP Integration endpoints
    mosip: {
        integrate: `${BASE_URL}/api/v1/mosip/integrate`,
        verifyAndSubmit: `${BASE_URL}/api/v1/mosip/verify-and-submit`,
        status: `${BASE_URL}/api/v1/mosip/status`,
        test: `${BASE_URL}/api/v1/mosip/test`,
        batchSubmit: `${BASE_URL}/api/v1/mosip/batch-submit`
    }
};

// --- DOM ELEMENTS ---
const views = {
    dashboard: document.getElementById('view-dashboard'),
    form: document.getElementById('view-form'),
    upload: document.getElementById('view-upload'),
    verify: document.getElementById('view-verify'),
    success: document.getElementById('view-success'),
    review: document.getElementById('view-review'),
    mosip: document.getElementById('view-mosip'),
    mosipStatus: document.getElementById('view-mosip-status')
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
// MOSIP elements
const mosipConnectionStatusEl = document.getElementById('mosip-connection-status');
const mosipFooterStatusEl = document.getElementById('mosip-footer-status');
const mosipStatusInputEl = document.getElementById('mosip-status-input');
const mosipStatusCheckBtn = document.getElementById('mosip-status-check');
const mosipTestBtn = document.getElementById('mosip-test-btn');
const submitToMosipBtn = document.getElementById('submit-to-mosip');
const mosipLoadingEl = document.getElementById('mosip-loading');
const mosipResultEl = document.getElementById('mosip-result');
const mosipStatusLoadingEl = document.getElementById('mosip-status-loading');
const mosipStatusResultEl = document.getElementById('mosip-status-result');
const recentRegistrationsEl = document.getElementById('recent-registrations');
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
    // Hide every view first
    Object.values(views).forEach(el => el && el.classList.add('d-none'));

    // Accept either the full element id (e.g., "view-mosip-status") or the short key (e.g., "mosipStatus")
    const direct = document.getElementById(viewName);
    if (direct) {
        direct.classList.remove('d-none');
        return;
    }

    const key = viewName.replace('view-', '');
    if (views[key]) {
        views[key].classList.remove('d-none');
    }
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
        selectedDocs.handwritten = file;
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
        const docTypeMap = { name: 'aadhar', address: 'dl', dob: 'birth', handwritten: 'handwritten' };
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
            const filterKeys = key === 'name'
                ? ['name', 'full_name']
                : key === 'address'
                ? ['address', 'addr', 'city', 'state', 'pincode']
                : key === 'dob'
                ? ['dob', 'date_of_birth', 'date-of-birth', 'birth_date', 'birthdate', 'date']
                : null;

            if (filterKeys) {
                // Include all matching keys in order to show city/state/pincode for address docs
                const collected = {};
                filterKeys.forEach(fk => {
                    if (!fields || !Object.prototype.hasOwnProperty.call(fields, fk)) return;
                    const v = fields[fk];
                    const val = (v && typeof v === 'object' && 'value' in v) ? v.value : v;
                    if (val !== undefined && val !== null && String(val).trim() !== '') {
                        collected[fk] = String(val).trim();
                    }
                });

                // If address doc is missing city/state/pincode, try to surface them from raw OCR text for display only
                if (key === 'address' && item.rawText) {
                    const rt = String(item.rawText);
                    if (!collected.city) {
                        const m = rt.match(/city\s*[:\-]?\s*([^\n,]+)/i);
                        if (m && m[1].trim()) collected.city = m[1].trim();
                    }
                    if (!collected.state) {
                        const m = rt.match(/state\s*[:\-]?\s*([^\n,]+)/i);
                        if (m && m[1].trim()) collected.state = m[1].trim();
                    }
                    if (!collected.pincode) {
                        const m = rt.match(/(?:pin\s*code|pincode|zip\s*code|zipcode|zip)\s*[:\-]?\s*(\d{4,10})/i);
                        if (m && m[1].trim()) collected.pincode = m[1].trim();
                    }
                }

                if (key === 'address') {
                    // Build a single-line address string
                    const parts = [];
                    if (collected.address || collected.addr) parts.push(collected.address || collected.addr);
                    if (collected.city) parts.push(collected.city);
                    if (collected.state) parts.push(collected.state);
                    if (collected.pincode) parts.push(collected.pincode);
                    const joined = parts.filter(Boolean).join(', ');
                    if (joined) {
                        lines.push(joined);
                    } else {
                        // fallback to individual lines if nothing joined
                        Object.entries(collected).forEach(([fk, val]) => lines.push(`${fk}: ${val}`));
                    }
                } else {
                    Object.entries(collected).forEach(([fk, val]) => lines.push(`${fk}: ${val}`));
                }
            } else {
                const seen = new Set();
                const normVal = (k, v) => {
                    const val = (v && typeof v === 'object' && 'value' in v) ? v.value : v;
                    if (val === undefined || val === null) return '';
                    let s = String(val).trim();
                    if (!s) return '';
                    if (key === 'handwritten' && k === 'email') {
                        s = s.replace(/^id:\s*/i, '');
                    }
                    return s;
                };

                if (key === 'handwritten') {
                    const ordered = ['name', 'dob', 'gender', 'address', 'city', 'state', 'pincode', 'phone', 'email'];
                    const labelMap = {
                        name: 'Name',
                        dob: 'Date of Birth',
                        gender: 'Gender',
                        address: 'Address',
                        city: 'City',
                        state: 'State',
                        pincode: 'Pincode',
                        phone: 'Phone',
                        email: 'Email',
                    };
                    const fmt = (k, v) => `${labelMap[k] || k}: ${v}`;

                    // Merge duplicate keys (case-insensitive) so state/pincode/etc. only show once.
                    const merged = {};
                    Object.entries(fields || {}).forEach(([k, v]) => {
                        const keyLc = String(k || '').toLowerCase();
                        const val = normVal(k, v);
                        if (!val) return;
                        if (!merged[keyLc]) merged[keyLc] = val;
                    });

                    ordered.forEach(k => {
                        if (merged[k]) {
                            lines.push(fmt(k, merged[k]));
                            seen.add(k);
                        }
                    });

                    Object.entries(merged).forEach(([k, v]) => {
                        if (ordered.includes(k)) return;
                        lines.push(fmt(k, v));
                    });
                } else {
                    Object.entries(fields || {}).forEach(([k, v]) => {
                        const val = normVal(k, v);
                        if (val && !seen.has(k)) {
                            seen.add(k);
                            lines.push(`${k}: ${val}`);
                        }
                    });
                }
            }
            // Prefer mapped fields; if empty, show placeholder until user edits/saves
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
        const docTypeMap = { name: 'aadhar', address: 'dl', dob: 'birth', handwritten: 'handwritten' };
        const document_type = docTypeMap[currentDocKey] || null;

        const mapRes = await fetch(ENDPOINTS.map, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: newText, user, document_type })
        });
        if (!mapRes.ok) throw new Error(`Update failed (${mapRes.status})`);
        const mapJson = await mapRes.json();
        let fields = mapJson.mapped || mapJson.mapped_fields || mapJson.data || mapJson;
        let verification = mapJson.verification || null;

        // Always normalize DOB edits against form DOB and ensure only a single DOB field
        if (currentDocKey === 'dob') {
            const userDob = (buildUserFromUI().dob || '').trim();

            const parseDob = (s) => {
                if (!s) return '';
                const stripped = s.toLowerCase().replace(/dob[^0-9]+/i, ' ').trim();
                const parts = (stripped.match(/\d+/g) || []).map(Number);
                if (parts.length < 3) return '';
                let y, m, d;
                // Try year first
                if (String(parts[0]).length === 4) {
                    [y, m, d] = parts;
                } else if (String(parts[2]).length === 4) {
                    [m, d, y] = parts;
                } else if (String(parts[1]).length === 4) {
                    [m, y, d] = parts;
                } else {
                    // Assume last is year (2-digit allowed)
                    [m, d, y] = parts;
                    if (y < 100) y = 2000 + y;
                }
                // Swap if month/day look inverted
                if (m > 12 && d <= 12) {
                    [m, d] = [d, m];
                }
                if (m < 1 || m > 12 || d < 1 || d > 31) return '';
                const pad = (n) => String(n).padStart(2, '0');
                return `${y}-${pad(m)}-${pad(d)}`;
            };

            const normUser = parseDob(userDob);
            const normEdit = parseDob(newText);
            let dobConf = 0.6;
            if (normUser && normEdit) dobConf = normUser === normEdit ? 1.0 : 0.55;
            fields = { dob: { value: newText, confidence: dobConf } };
            verification = { score: dobConf, overall_confidence: dobConf };
        }

        // Persist updated results for finalize and confidence panel
        reviewResults = reviewResults || {};
        const prev = reviewResults[currentDocKey] || {};
        reviewResults[currentDocKey] = {
            fileName: prev.fileName,
            url: prev.url,
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

// --- MOSIP INTEGRATION ---
function setMosipStatus(text, badgeClass = 'bg-light text-dark') {
    if (mosipConnectionStatusEl) {
        mosipConnectionStatusEl.innerHTML = text;
    }
    if (mosipFooterStatusEl) {
        mosipFooterStatusEl.className = `badge ${badgeClass}`;
        mosipFooterStatusEl.innerHTML = text;
    }
}

async function testMOSIPConnection() {
    try {
        setMosipStatus('<i class="fas fa-circle-notch fa-spin me-1"></i> Testing MOSIP...', 'bg-light text-dark');
        const resp = await fetch(ENDPOINTS.mosip.test);
        const data = await resp.json();
        if (resp.ok) {
            setMosipStatus('<i class="fas fa-check-circle me-1"></i> Connected to MOSIP', 'bg-success text-white');
            return true;
        }
        throw new Error(data.detail || 'Connection failed');
    } catch (err) {
        console.error('MOSIP Connection Error:', err);
        setMosipStatus(`<i class="fas fa-times-circle me-1"></i> MOSIP offline: ${err.message}`, 'bg-danger text-white');
        return false;
    }
}

async function submitToMOSIP() {
    if (!reviewResults) {
        alert('Please process documents first before submitting to MOSIP');
        return;
    }

    const user = buildUserFromUI();
    // Move to MOSIP view immediately so user sees progress and any errors
    switchView('view-mosip');
    if (mosipLoadingEl) mosipLoadingEl.classList.remove('d-none');
    if (mosipResultEl) mosipResultEl.innerHTML = '<div class="alert alert-info">Submitting to MOSIP...</div>';

    try {
        const connected = await testMOSIPConnection();
        if (!connected) throw new Error('Cannot connect to MOSIP sandbox');

        const documents = [];
        if (selectedDocs.name && reviewResults.name) {
            documents.push({ file: selectedDocs.name, data: reviewResults.name, type: 'POI' });
        }
        if (selectedDocs.address && reviewResults.address) {
            documents.push({ file: selectedDocs.address, data: reviewResults.address, type: 'POA' });
        }
        if (selectedDocs.dob && reviewResults.dob) {
            documents.push({ file: selectedDocs.dob, data: reviewResults.dob, type: 'DOB' });
        }
        if (documents.length === 0) throw new Error('No documents to submit to MOSIP');

        const primaryDoc = documents[0];
        const formData = new FormData();
        formData.append('file', primaryDoc.file);

        // Only send manual fields tied to an uploaded document; skip missing docs to avoid false verification failures
        const manualData = {};
        if (selectedDocs.name && user.name) manualData.Name = user.name;
        if (selectedDocs.dob && user.dob) manualData.Date_of_Birth = user.dob;
        if (selectedDocs.name && user.gender) manualData.Gender = user.gender; // gender usually with identity doc
        if (selectedDocs.address && user.address) manualData.Address = user.address;
        if (selectedDocs.name && user.phone) manualData.Phone = user.phone;
        if (selectedDocs.name && user.email) manualData.Email = user.email;
        if (Object.keys(manualData).length) {
            formData.append('manual_data', JSON.stringify(manualData));
        }

        // Allow a slightly lower threshold to reduce false negatives; adjust here if needed
        formData.append('verification_threshold', '0.6');

        const resp = await fetch(ENDPOINTS.mosip.integrate, { method: 'POST', body: formData });
        const result = await resp.json();
        if (!resp.ok || result.status !== 'success') {
            const vr = result.verification_results;
            const vrMsg = vr && vr.overall_confidence !== undefined
                ? ` (confidence ${vr.overall_confidence})`
                : '';
            throw new Error((result.message || result.detail || 'MOSIP registration failed') + vrMsg);
        }

        const preRegId = result.pre_registration_id;
        switchView('view-mosip');
        if (mosipResultEl) {
            mosipResultEl.innerHTML = `
                <div class="alert alert-success">
                    <h4 class="alert-heading">✓ Registration Successful!</h4>
                    <p>Your pre-registration has been submitted to MOSIP.</p>
                    <hr>
                    <p class="mb-0">
                        <strong>Pre-registration ID:</strong> ${preRegId}<br>
                        <strong>Next Steps:</strong> ${result.message || 'Awaiting verification'}
                    </p>
                </div>
                <div class="mt-3 d-flex gap-2">
                    <button class="btn btn-outline-primary" onclick="checkMOSIPStatus('${preRegId}')">Check Status</button>
                    <button class="btn btn-outline-secondary" onclick='downloadMOSIPReport(${JSON.stringify(result)})'>Download Registration Report</button>
                </div>
            `;
        }

        localStorage.setItem('last_mosip_pre_reg_id', preRegId);
        localStorage.setItem('last_mosip_response', JSON.stringify(result));
    } catch (err) {
        console.error('MOSIP Submission Error:', err);
        if (mosipResultEl) {
            mosipResultEl.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">✗ Registration Failed</h4>
                    <p>${err.message}</p>
                    <hr>
                    <p class="mb-0">Please check your documents and try again.</p>
                </div>
            `;
        }
    } finally {
        if (mosipLoadingEl) mosipLoadingEl.classList.add('d-none');
    }
}

async function checkMOSIPStatus(preRegId) {
    const id = preRegId || mosipStatusInputEl?.value || localStorage.getItem('last_mosip_pre_reg_id');
    if (!id) {
        alert('Please enter a Pre-registration ID');
        return;
    }
    if (mosipStatusLoadingEl) mosipStatusLoadingEl.classList.remove('d-none');
    if (mosipStatusResultEl) mosipStatusResultEl.innerHTML = '';
    try {
        const resp = await fetch(`${ENDPOINTS.mosip.status}/${id}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Failed to fetch status');

        let statusClass = 'secondary';
        let statusIcon = '⏳';
        const status = (data.status || '').toLowerCase();
        if (status.includes('approved') || status.includes('success')) { statusClass = 'success'; statusIcon = '✓'; }
        else if (status.includes('rejected') || status.includes('failed')) { statusClass = 'danger'; statusIcon = '✗'; }
        else if (status.includes('pending') || status.includes('processing')) { statusClass = 'warning'; statusIcon = '🔄'; }

        if (mosipStatusResultEl) {
            mosipStatusResultEl.innerHTML = `
                <div class="alert alert-info">
                    <h4 class="alert-heading">Registration Status</h4>
                    <p><strong>Pre-registration ID:</strong> ${id}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${statusClass}">${statusIcon} ${data.status || 'Unknown'}</span></p>
                    ${data.details ? `<p><strong>Details:</strong> ${JSON.stringify(data.details)}</p>` : ''}
                </div>`;
        }
        setMosipStatus(`<i class="fas fa-check-circle me-1"></i> MOSIP: ${data.status || 'OK'}`, `bg-${statusClass} ${statusClass === 'warning' ? 'text-dark' : 'text-white'}`);
        localStorage.setItem('last_mosip_pre_reg_id', id);
        if (recentRegistrationsEl) {
            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.textContent = `${id} — ${data.status || 'Unknown'}`;
            recentRegistrationsEl.prepend(item);
        }
    } catch (err) {
        console.error('Status Check Error:', err);
        if (mosipStatusResultEl) {
            mosipStatusResultEl.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">Status Check Failed</h4>
                    <p>${err.message}</p>
                </div>`;
        }
        setMosipStatus(`<i class="fas fa-times-circle me-1"></i> Status check failed`, 'bg-danger text-white');
    } finally {
        if (mosipStatusLoadingEl) mosipStatusLoadingEl.classList.add('d-none');
    }
}

function downloadMOSIPReport(result) {
    try {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(result, null, 2));
        const a = document.createElement('a');
        a.setAttribute('href', dataStr);
        a.setAttribute('download', `mosip_registration_${result.pre_registration_id || Date.now()}.json`);
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (err) {
        console.error('Download failed:', err);
        alert('Failed to download report');
    }
}

async function submitBatchToMOSIP() {
    if (!reviewResults || Object.keys(reviewResults).length === 0) {
        alert('Please process documents first');
        return;
    }
    const formData = new FormData();
    const files = [];
    if (selectedDocs.name) { formData.append('files', selectedDocs.name); files.push(selectedDocs.name.name); }
    if (selectedDocs.address) { formData.append('files', selectedDocs.address); files.push(selectedDocs.address.name); }
    if (selectedDocs.dob) { formData.append('files', selectedDocs.dob); files.push(selectedDocs.dob.name); }
    if (!files.length) { alert('No documents to submit'); return; }

    const user = buildUserFromUI();
    const verificationData = files.map(() => ({
        Name: user.name,
        Date_of_Birth: user.dob,
        Gender: user.gender,
        Address: user.address
    }));
    formData.append('verification_data', JSON.stringify(verificationData));

    try {
        const resp = await fetch(ENDPOINTS.mosip.batchSubmit, { method: 'POST', body: formData });
        const result = await resp.json();
        if (!resp.ok) throw new Error(result.detail || 'Batch submission failed');
        alert(`Batch submission completed:\nSuccess: ${result.successful}\nFailed: ${result.failed}`);
        return result;
    } catch (err) {
        console.error('Batch Submission Error:', err);
        alert(`Batch submission failed: ${err.message}`);
        throw err;
    }
}

function checkLastRegistration() {
    const lastId = localStorage.getItem('last_mosip_pre_reg_id');
    if (lastId) {
        checkMOSIPStatus(lastId);
    } else {
        alert('No previous registration found');
    }
}

function checkPreviousRegistration() {
    const raw = localStorage.getItem('last_mosip_response');
    if (raw && mosipResultEl) {
        const result = JSON.parse(raw);
        mosipResultEl.innerHTML = `
            <div class="alert alert-secondary">
                <h5 class="alert-heading">Last submission</h5>
                <p><strong>Pre-registration ID:</strong> ${result.pre_registration_id || 'N/A'}</p>
                <p><strong>Status:</strong> ${result.status || 'N/A'}</p>
            </div>`;
    } else {
        alert('No previous registration found');
    }
}

function initMOSIPIntegration() {
    window.addEventListener('load', () => setTimeout(testMOSIPConnection, 500));
    submitToMosipBtn?.addEventListener('click', submitToMOSIP);
    mosipStatusCheckBtn?.addEventListener('click', () => checkMOSIPStatus());
    mosipTestBtn?.addEventListener('click', testMOSIPConnection);
}

// Expose for inline onclick handlers
window.testMOSIPConnection = testMOSIPConnection;
window.submitToMOSIP = submitToMOSIP;
window.checkMOSIPStatus = checkMOSIPStatus;
window.downloadMOSIPReport = downloadMOSIPReport;
window.submitBatchToMOSIP = submitBatchToMOSIP;
window.checkLastRegistration = checkLastRegistration;
window.checkPreviousRegistration = checkPreviousRegistration;

initMOSIPIntegration();

// No drag & drop after removing the upload zone