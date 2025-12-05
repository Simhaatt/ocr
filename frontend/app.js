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
    upload: document.getElementById('view-upload'),
    verify: document.getElementById('view-verify'),
    success: document.getElementById('view-success')
};

const fileInput = document.getElementById('fileInput');
const loadingSpinner = document.getElementById('loading-spinner');
const verifyForm = document.getElementById('verify-form');
const previewImg = document.getElementById('preview-img');
const uploadZone = document.querySelector('.upload-zone');

let currentObjectUrl = null; // Track image memory for privacy cleanup

// --- SWITCH SCREENS ---
function switchView(viewName) {
    Object.values(views).forEach(el => el.classList.add('d-none'));
    views[viewName.replace('view-', '')].classList.remove('d-none');
}

// --- MAIN UPLOAD LOGIC (Merged) ---
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // 1. PRIVACY CLEANUP: Revoke old image memory
    if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
    }
    currentObjectUrl = URL.createObjectURL(file);
    previewImg.src = currentObjectUrl;

    // 2. UI UPDATES
    document.querySelector('.upload-zone').classList.add('d-none');
    loadingSpinner.classList.remove('d-none');

    const formData = new FormData();
    // Backend expects field name 'file' at /api/v1/ocr/extract-text
    formData.append('file', file);

    try {
        console.log("🚀 Step 1: Sending to OCR extraction...");
        // STEP A: OCR Extract Text (image/pdf -> raw text)
        const ocrRes = await fetch(ENDPOINTS.ocrExtract, { method: 'POST', body: formData });
        if (!ocrRes.ok) throw new Error(`OCR Extraction Failed: ${ocrRes.status}`);

        const ocrJson = await ocrRes.json();
        const rawText = ocrJson.extracted_text || ocrJson.raw_text || ocrJson.data?.raw_text || "";

        console.log("🚀 Step 2: Sending to Mapping & Verification...");
        // STEP B: Map & Verify
        const mapRes = await fetch(ENDPOINTS.map, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: rawText, user: {} })
        });
        
        if (!mapRes.ok) throw new Error(`Mapping Failed: ${mapRes.status}`);
        
        const mapJson = await mapRes.json();
        // Handle different JSON structures from backend
        const fields = mapJson.data || mapJson.mapped_fields || mapJson.mapped || mapJson;

        renderForm(fields);
        switchView('view-verify');

    } catch (err) {
        console.error(err);
        alert(`Error: ${err.message}. Is Backend running on port 8000?`);
        // Reset UI on error
        document.querySelector('.upload-zone').classList.remove('d-none');
        fileInput.value = ''; // clear input
    } finally {
        loadingSpinner.classList.add('d-none');
    }
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
    // 1. Scrape data from inputs
    const payload = {};
    verifyForm.querySelectorAll('input[data-key]').forEach(input => {
        const key = input.getAttribute('data-key');
        payload[key] = input.value;
    });

    console.log("📦 Submitting Payload:", payload);

    try {
        // 2. Try Real Backend Submit
        const res = await fetch(ENDPOINTS.submit, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ data: payload }) // Wrapping in 'data' key
        });

        if (!res.ok) throw new Error("Backend rejected submission");

        console.log("✅ Backend Submission Success");

    } catch (err) {
        console.warn('⚠️ Backend Submit Failed/Offline. Falling back to local download.');
        console.error(err);

        // 3. FALLBACK: Download JSON (Saves the demo if server fails)
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(payload));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "mosip_packet.json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    // 4. PRIVACY CLEANUP (Crucial for MOSIP)
    if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
        currentObjectUrl = null;
        previewImg.src = '';
    }

    // 5. Show Success Screen
    switchView('view-success');
}

// --- DRAG & DROP HANDLERS ---
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    uploadZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});

['dragenter', 'dragover'].forEach(evt => {
    uploadZone.addEventListener(evt, () => uploadZone.classList.add('drag-over'), false);
});

['dragleave', 'drop'].forEach(evt => {
    uploadZone.addEventListener(evt, () => uploadZone.classList.remove('drag-over'), false);
});

uploadZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        // Trigger the merged listener above
        fileInput.dispatchEvent(new Event('change'));
    }
}, false);