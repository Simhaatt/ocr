// --- CONFIGURATION ---
const BASE_URL = "http://localhost:8000";
const ENDPOINTS = {
    // OCR: upload image/pdf as 'file'
    ocrExtract: `${BASE_URL}/api/v1/ocr/extract-text`,
    // Mapping + Verification using extracted raw text
    map: `${BASE_URL}/api/v1/map-and-verify`,
    // MOSIP Integration endpoints (NEW)
    mosip: {
        integrate: `${BASE_URL}/api/v1/mosip/integrate`,
        verifyAndSubmit: `${BASE_URL}/api/v1/mosip/verify-and-submit`,
        status: `${BASE_URL}/api/v1/mosip/status`,
        test: `${BASE_URL}/api/v1/mosip/test`,
        batchSubmit: `${BASE_URL}/api/v1/mosip/batch-submit`
    }
};

// --- DOM ELEMENTS (Add MOSIP elements) ---
const views = {
    dashboard: document.getElementById('view-dashboard'),
    form: document.getElementById('view-form'),
    upload: document.getElementById('view-upload'),
    verify: document.getElementById('view-verify'),
    success: document.getElementById('view-success'),
    review: document.getElementById('view-review'),
    mosip: document.getElementById('view-mosip'), // NEW MOSIP view
    mosipStatus: document.getElementById('view-mosip-status') // NEW MOSIP status view
};

// MOSIP specific elements (add these to your HTML)
const mosipSubmitBtn = document.getElementById('mosip-submit-btn');
const mosipBackBtn = document.getElementById('mosip-back-btn');
const mosipStatusCheckBtn = document.getElementById('mosip-status-check');
const mosipPreRegIdEl = document.getElementById('mosip-pre-reg-id');
const mosipStatusEl = document.getElementById('mosip-status');
const mosipTestBtn = document.getElementById('mosip-test-btn');
const mosipConnectionStatus = document.getElementById('mosip-connection-status');

// Update switchView to include MOSIP views
function switchView(viewName) {
    Object.values(views).forEach(el => el && el.classList.add('d-none'));
    const key = viewName.replace('view-', '');
    if (views[key]) {
        views[key].classList.remove('d-none');
    }
}

// Add MOSIP button to your review page (modify your HTML)
// Add this button near the finalSubmitBtn in your review page HTML:
// <button id="submit-to-mosip" class="btn btn-primary">Submit to MOSIP</button>
const submitToMosipBtn = document.getElementById('submit-to-mosip');

// --- MOSIP INTEGRATION FUNCTIONS ---

// Test MOSIP connection
async function testMOSIPConnection() {
    try {
        if (mosipConnectionStatus) {
            mosipConnectionStatus.innerHTML = '<span class="text-info">Testing connection...</span>';
        }
        
        const response = await fetch(ENDPOINTS.mosip.test);
        const data = await response.json();
        
        if (response.ok) {
            if (mosipConnectionStatus) {
                mosipConnectionStatus.innerHTML = 
                    '<span class="text-success">✓ Connected to MOSIP Sandbox</span>';
            }
            console.log('MOSIP Connection Test:', data);
            return true;
        } else {
            throw new Error(data.detail || 'Connection failed');
        }
    } catch (error) {
        console.error('MOSIP Connection Error:', error);
        if (mosipConnectionStatus) {
            mosipConnectionStatus.innerHTML = 
                `<span class="text-danger">✗ Connection failed: ${error.message}</span>`;
        }
        return false;
    }
}

// Submit all documents and data to MOSIP
async function submitToMOSIP() {
    if (!reviewResults) {
        alert('Please process documents first before submitting to MOSIP');
        return;
    }

    const user = buildUserFromUI();
    const loadingEl = document.getElementById('mosip-loading');
    const resultEl = document.getElementById('mosip-result');
    
    if (loadingEl) loadingEl.classList.remove('d-none');
    if (resultEl) resultEl.innerHTML = '';

    try {
        // First, test connection
        const isConnected = await testMOSIPConnection();
        if (!isConnected) {
            throw new Error('Cannot connect to MOSIP sandbox. Please check configuration.');
        }

        // For each document, submit to MOSIP
        const results = [];
        const documents = [];

        // Process name document
        if (selectedDocs.name && reviewResults.name) {
            documents.push({
                file: selectedDocs.name,
                data: reviewResults.name,
                type: 'POI' // Proof of Identity
            });
        }

        // Process address document
        if (selectedDocs.address && reviewResults.address) {
            documents.push({
                file: selectedDocs.address,
                data: reviewResults.address,
                type: 'POA' // Proof of Address
            });
        }

        // Process DOB document
        if (selectedDocs.dob && reviewResults.dob) {
            documents.push({
                file: selectedDocs.dob,
                data: reviewResults.dob,
                type: 'DOB' // Date of Birth proof
            });
        }

        if (documents.length === 0) {
            throw new Error('No documents to submit to MOSIP');
        }

        // Submit first document (usually ID) for pre-registration
        const primaryDoc = documents[0];
        
        // Create FormData for the primary document
        const formData = new FormData();
        formData.append('file', primaryDoc.file);
        
        // Add manual verification data if available
        const manualData = {};
        if (user.name) manualData.Name = user.name;
        if (user.dob) manualData.Date_of_Birth = user.dob;
        if (user.gender) manualData.Gender = user.gender;
        if (user.address) manualData.Address = user.address;
        if (user.phone) manualData.Phone = user.phone;
        if (user.email) manualData.Email = user.email;
        
        if (Object.keys(manualData).length > 0) {
            formData.append('manual_data', JSON.stringify(manualData));
        }

        // Submit to MOSIP
        console.log('🚀 Submitting to MOSIP...');
        const response = await fetch(ENDPOINTS.mosip.integrate, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            // Store pre-registration ID
            const preRegId = result.pre_registration_id;
            
            // Switch to MOSIP success view
            switchView('view-mosip');
            
            // Display success message
            if (resultEl) {
                resultEl.innerHTML = `
                    <div class="alert alert-success">
                        <h4 class="alert-heading">✓ Registration Successful!</h4>
                        <p>Your pre-registration has been submitted to MOSIP.</p>
                        <hr>
                        <p class="mb-0">
                            <strong>Pre-registration ID:</strong> ${preRegId}<br>
                            <strong>Next Steps:</strong> ${result.message || 'Awaiting verification'}
                        </p>
                    </div>
                    <div class="mt-3">
                        <button class="btn btn-outline-primary" onclick="checkMOSIPStatus('${preRegId}')">
                            Check Registration Status
                        </button>
                        <button class="btn btn-outline-secondary" onclick="downloadMOSIPReport(${JSON.stringify(result)})">
                            Download Registration Report
                        </button>
                    </div>
                `;
            }
            
            // Store in localStorage for status checking
            localStorage.setItem('last_mosip_pre_reg_id', preRegId);
            localStorage.setItem('last_mosip_response', JSON.stringify(result));
            
            console.log('MOSIP Registration Success:', result);
            
        } else {
            throw new Error(result.message || result.detail || 'MOSIP registration failed');
        }
        
    } catch (error) {
        console.error('MOSIP Submission Error:', error);
        if (resultEl) {
            resultEl.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">✗ Registration Failed</h4>
                    <p>${error.message}</p>
                    <hr>
                    <p class="mb-0">Please check your documents and try again.</p>
                </div>
            `;
        }
    } finally {
        if (loadingEl) loadingEl.classList.add('d-none');
    }
}

// Check MOSIP registration status
async function checkMOSIPStatus(preRegId) {
    if (!preRegId) {
        preRegId = document.getElementById('mosip-status-input')?.value || 
                   localStorage.getItem('last_mosip_pre_reg_id');
    }
    
    if (!preRegId) {
        alert('Please enter a Pre-registration ID');
        return;
    }
    
    const statusLoading = document.getElementById('mosip-status-loading');
    const statusResult = document.getElementById('mosip-status-result');
    
    if (statusLoading) statusLoading.classList.remove('d-none');
    if (statusResult) statusResult.innerHTML = '';
    
    try {
        const response = await fetch(`${ENDPOINTS.mosip.status}/${preRegId}`);
        const data = await response.json();
        
        if (response.ok) {
            if (statusResult) {
                let statusHtml = `
                    <div class="alert alert-info">
                        <h4 class="alert-heading">Registration Status</h4>
                        <p><strong>Pre-registration ID:</strong> ${preRegId}</p>
                `;
                
                // Parse and display status
                if (data.status) {
                    const status = data.status;
                    let statusClass = 'secondary';
                    let statusIcon = '⏳';
                    
                    if (status.includes('approved') || status.includes('success')) {
                        statusClass = 'success';
                        statusIcon = '✓';
                    } else if (status.includes('rejected') || status.includes('failed')) {
                        statusClass = 'danger';
                        statusIcon = '✗';
                    } else if (status.includes('pending') || status.includes('processing')) {
                        statusClass = 'warning';
                        statusIcon = '🔄';
                    }
                    
                    statusHtml += `
                        <p><strong>Status:</strong> 
                            <span class="badge bg-${statusClass}">${statusIcon} ${status}</span>
                        </p>
                    `;
                }
                
                // Display additional details if available
                if (data.details) {
                    statusHtml += `<p><strong>Details:</strong> ${JSON.stringify(data.details)}</p>`;
                }
                
                statusHtml += `</div>`;
                statusResult.innerHTML = statusHtml;
            }
            
            console.log('MOSIP Status:', data);
        } else {
            throw new Error(data.detail || 'Failed to fetch status');
        }
        
    } catch (error) {
        console.error('Status Check Error:', error);
        if (statusResult) {
            statusResult.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">Status Check Failed</h4>
                    <p>${error.message}</p>
                </div>
            `;
        }
    } finally {
        if (statusLoading) statusLoading.classList.add('d-none');
    }
}

// Download MOSIP registration report
function downloadMOSIPReport(result) {
    try {
        const dataStr = "data:text/json;charset=utf-8," + 
                       encodeURIComponent(JSON.stringify(result, null, 2));
        const a = document.createElement('a');
        a.setAttribute('href', dataStr);
        a.setAttribute('download', `mosip_registration_${result.pre_registration_id || Date.now()}.json`);
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (error) {
        console.error('Download failed:', error);
        alert('Failed to download report');
    }
}

// Batch submit multiple documents to MOSIP
async function submitBatchToMOSIP() {
    if (!reviewResults || Object.keys(reviewResults).length === 0) {
        alert('Please process documents first');
        return;
    }

    const formData = new FormData();
    const files = [];
    
    // Add all files
    if (selectedDocs.name) {
        formData.append('files', selectedDocs.name);
        files.push(selectedDocs.name.name);
    }
    if (selectedDocs.address) {
        formData.append('files', selectedDocs.address);
        files.push(selectedDocs.address.name);
    }
    if (selectedDocs.dob) {
        formData.append('files', selectedDocs.dob);
        files.push(selectedDocs.dob.name);
    }

    if (files.length === 0) {
        alert('No documents to submit');
        return;
    }

    // Add verification data
    const user = buildUserFromUI();
    const verificationData = files.map(() => ({
        Name: user.name,
        Date_of_Birth: user.dob,
        Gender: user.gender,
        Address: user.address
    }));
    
    formData.append('verification_data', JSON.stringify(verificationData));

    try {
        const response = await fetch(ENDPOINTS.mosip.batchSubmit, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (response.ok) {
            alert(`Batch submission completed:\nSuccess: ${result.successful}\nFailed: ${result.failed}`);
            console.log('Batch Submission Result:', result);
            return result;
        } else {
            throw new Error(result.detail || 'Batch submission failed');
        }
    } catch (error) {
        console.error('Batch Submission Error:', error);
        alert(`Batch submission failed: ${error.message}`);
        throw error;
    }
}

// Initialize MOSIP integration
function initMOSIPIntegration() {
    // Test connection on page load
    window.addEventListener('load', () => {
        // Test MOSIP connection but don't block UI
        setTimeout(testMOSIPConnection, 1000);
    });

    // Add MOSIP submit button to review page
    if (submitToMosipBtn) {
        submitToMosipBtn.addEventListener('click', submitToMOSIP);
    }

    // Add MOSIP status check button
    if (mosipStatusCheckBtn) {
        mosipStatusCheckBtn.addEventListener('click', () => {
            checkMOSIPStatus();
        });
    }

    // Add MOSIP test button
    if (mosipTestBtn) {
        mosipTestBtn.addEventListener('click', testMOSIPConnection);
    }

    // Add MOSIP back button
    if (mosipBackBtn) {
        mosipBackBtn.addEventListener('click', () => {
            switchView('view-review');
        });
    }
}

// Add MOSIP button to your review page render function
function modifyReviewPageForMOSIP() {
    // Add MOSIP submit button to review page if it doesn't exist
    if (!submitToMosipBtn && document.getElementById('review-buttons')) {
        const reviewButtons = document.getElementById('review-buttons');
        const mosipBtn = document.createElement('button');
        mosipBtn.id = 'submit-to-mosip';
        mosipBtn.className = 'btn btn-primary ms-2';
        mosipBtn.innerHTML = '<i class="fas fa-cloud-upload"></i> Submit to MOSIP';
        reviewButtons.appendChild(mosipBtn);
        
        mosipBtn.addEventListener('click', submitToMOSIP);
    }
}

// Update the existing submitData function to include MOSIP option
const originalSubmitData = window.submitData;
window.submitData = async function() {
    await originalSubmitData();
    // After rendering review, add MOSIP button
    modifyReviewPageForMOSIP();
};

// Expose MOSIP functions globally
window.testMOSIPConnection = testMOSIPConnection;
window.submitToMOSIP = submitToMOSIP;
window.checkMOSIPStatus = checkMOSIPStatus;
window.downloadMOSIPReport = downloadMOSIPReport;
window.submitBatchToMOSIP = submitBatchToMOSIP;

// Initialize MOSIP integration
initMOSIPIntegration();

// Add this to your existing initialization
console.log('MOSIP Integration Module Loaded');
