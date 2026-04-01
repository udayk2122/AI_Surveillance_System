// ==========================================
// GLOBAL CONFIG & STATE
// ==========================================
const API_BASE = "/api/auth";
let selectedFile = null;
let threatChart = null;

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const regForm = document.getElementById('regForm');
    const otpForm = document.getElementById('otpSection');
    const loginForm = document.querySelector('.auth-form form'); 

    // Registration Form
    if (regForm) {
        regForm.addEventListener('submit', async (e) => {
            e.preventDefault(); 
            e.stopPropagation(); 
            await handleSendOTPLogic();
            return false;
        });
    }

    // OTP Form
    if (otpForm) {
        otpForm.addEventListener('submit', async (e) => {
            e.preventDefault(); 
            e.stopPropagation();
            await handleRegisterLogic();
            return false;
        });
    }

    // Login Form
    if (loginForm && window.location.pathname.includes('login.html')) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleLoginLogic();
        });
    }

    // Load Nav/Footer and apply scroll effects
    loadInterfaceComponents();
});

// ==========================================
// UI & COMPONENT LOADING
// ==========================================
async function loadInterfaceComponents() {
    try {
        const navRes = await fetch('navbar.html');
        const navCont = document.getElementById('navbar-container');
        if (navCont) navCont.innerHTML = await navRes.text();

        const footRes = await fetch('footer.html');
        const footCont = document.getElementById('footer-container');
        if (footCont) footCont.innerHTML = await footRes.text();
        
        updateNavbarState(); 
    } catch (e) { 
        console.error("Components load error:", e); 
    }

    // Navbar Scroll Effect
    window.addEventListener('scroll', () => {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            window.scrollY > 50 ? navbar.classList.add('scrolled') : navbar.classList.remove('scrolled');
        }
    });

    // Fade-in Scroll Animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
}

// Global Custom Modal for Alerts
window.showMsg = (title, text, type = "info") => {
    const modalEl = document.getElementById('globalMsgModal');
    if (!modalEl) return alert(`${title}: ${text}`); // Fallback

    const header = document.getElementById('globalMsgHeader');
    const icon = document.getElementById('globalMsgIcon');
    
    document.getElementById('globalMsgTitle').innerText = title;
    document.getElementById('globalMsgText').innerText = text;

    header.className = 'modal-header text-white border-0';
    icon.className = 'fa-4x mb-3';

    if (type === 'success') {
        header.classList.add('bg-success');
        icon.classList.add('fas', 'fa-check-circle', 'text-success');
    } else if (type === 'error') {
        header.classList.add('bg-danger');
        icon.classList.add('fas', 'fa-times-circle', 'text-danger');
    } else {
        header.classList.add('bg-warning');
        icon.classList.add('fas', 'fa-exclamation-triangle', 'text-warning');
        header.classList.replace('text-white', 'text-dark');
    }

    const bsModal = new bootstrap.Modal(modalEl);
    bsModal.show();
};

// ==========================================
// AUTHENTICATION LOGIC
// ==========================================
function updateNavbarState() {
    const token = localStorage.getItem('guardian_token');
    if (token) {
        document.getElementById('nav-login')?.classList.add('d-none');
        document.getElementById('nav-register')?.classList.add('d-none');
        document.getElementById('nav-dash')?.classList.remove('d-none');
        document.getElementById('nav-logout')?.classList.remove('d-none');
    }
}

window.logoutUser = () => {
    localStorage.removeItem('guardian_token');
    window.location.href = 'index.html';
};

async function handleLoginLogic() {
    const email = document.getElementById('emailInput').value;
    const pass = document.getElementById('passInput').value;
    const btn = document.getElementById('loginBtn');
    
    if(!email || !pass) return showMsg("Required", "Please fill in all fields.", "error");

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username: email, password: pass })
        });
        const data = await res.json();
        
        if (res.ok) {
            localStorage.setItem('guardian_token', data.access_token);
            window.location.href = "dashboard.html";
        } else {
            showMsg("Login Failed", data.detail || "Invalid credentials", "error");
        }
    } catch(e) { 
        showMsg("Error", "Server connection failed.", "error"); 
    } finally { 
        btn.innerHTML = originalText; 
        btn.disabled = false; 
    }
}

async function handleSendOTPLogic() {
    const email = document.getElementById('regEmail').value;
    const btn = document.getElementById('sendBtn');
    
    if(!email || !email.includes('@')) return showMsg("Invalid", "Please enter a valid email address", "warning");

    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/send-reg-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        if (res.ok) {
            document.getElementById('regForm').style.display = 'none';
            document.getElementById('otpSection').style.display = 'block';
            showMsg("Success", "OTP sent to " + email, "success");
        } else {
            const data = await res.json();
            showMsg("Error", data.detail || "Failed to send OTP", "error");
        }
    } catch(e) {
        console.error("Error", e);
        showMsg("Error", "Could not connect to server.", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function handleRegisterLogic() {
    const name = document.getElementById('regName').value;
    const email = document.getElementById('regEmail').value;
    const pass = document.getElementById('regPass').value;
    const otp = document.getElementById('otpInput').value;
    const btn = document.getElementById('verifyBtn');

    if(!otp) return showMsg("Required", "Please enter the OTP.", "warning");
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
    btn.disabled = true;

    try {
        const verifyRes = await fetch(`${API_BASE}/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, otp_code: otp, purpose: 'registration' })
        });
        
        if (!verifyRes.ok) throw new Error("Invalid or Expired OTP.");

        const regRes = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: name, email: email, password: pass })
        });

        if (regRes.ok) {
            showMsg("Welcome!", "Account created successfully.", "success");
            setTimeout(() => window.location.href = "login.html", 2000);
        } else {
            const data = await regRes.json();
            throw new Error(data.detail || "Registration failed.");
        }
    } catch(e) { 
        showMsg("Error", e.message, "error"); 
    } finally { 
        btn.innerHTML = originalText; 
        btn.disabled = false; 
    }
}

// ==========================================
// AI VIDEO ANALYSIS & DASHBOARD LOGIC
// ==========================================

// 1. Fetch Stats & Logs on Dashboard Load
window.loadDashboardData = async function() {
    const token = localStorage.getItem('guardian_token');
    if (!token) return;

    try {
        // Fetch HUD Stats
        const statsRes = await fetch('/api/surveillance/stats', { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        if (statsRes.ok) {
            const stats = await statsRes.json();
            
            // Safety check: Only update if the elements actually exist on the page
            const camStat = document.getElementById('stat-cameras');
            if (camStat) {
                camStat.innerText = stats.active_cameras < 10 ? '0'+stats.active_cameras : stats.active_cameras;
                document.getElementById('stat-detections').innerText = stats.detections_today;
                document.getElementById('stat-alerts').innerText = stats.unread_alerts < 10 ? '0'+stats.unread_alerts : stats.unread_alerts;
                
                updateChart(stats.chart_data);
            }
        }

        // Fetch Event Logs
        const logsRes = await fetch('/api/surveillance/logs', { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        if (logsRes.ok) {
            const logs = await logsRes.json();
            const tableBody = document.getElementById('logTableBody');
            
            if (tableBody) {
                tableBody.innerHTML = ''; // Clear existing table rows
                
                if(logs.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No recent threats detected.</td></tr>`;
                } else {
                    logs.forEach(log => {
                        // Color code based on confidence
                        let confValue = parseInt(log.confidence);
                        let colorClass = confValue > 80 ? 'text-danger' : 'text-warning';
                        
                        tableBody.innerHTML += `
                            <tr>
                                <td class="ps-4"><span class="badge bg-secondary">${log.time}</span></td>
                                <td><strong>${log.source.substring(0, 12)}...</strong></td>
                                <td><span class="${colorClass} fw-bold">${log.threat.toUpperCase()}</span></td>
                                <td>${log.confidence}</td>
                                <td class="text-end pe-4"><button class="btn btn-sm btn-dark"><i class="fas fa-eye"></i></button></td>
                            </tr>
                        `;
                    });
                }
            }
        }
    } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
    }
};

// 2. Handle File Selection UI
window.handleFileSelect = function(event) {
    const fileInput = event.target;
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const fileInfo = document.getElementById('fileInfo');
    const uploadForm = document.getElementById('uploadForm');

    if (fileInput.files && fileInput.files.length > 0) {
        selectedFile = fileInput.files[0];
        fileNameDisplay.textContent = selectedFile.name;
        uploadForm.classList.add('d-none');
        fileInfo.classList.remove('d-none');
    }
};

// 3. Send Video to Backend AI Engine
window.runAIAnalysis = async function() {
    if (!selectedFile) return showMsg("Warning", "Please select a video file first.", "warning");
    
    const token = localStorage.getItem('guardian_token');
    const btn = document.getElementById('analyzeBtn');
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Processing Video...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const response = await fetch('/api/surveillance/analyze', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }, // Require Authentication
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Update Video Player
            const feedContainer = document.querySelector('.feed-container');
            if (feedContainer) {
                feedContainer.innerHTML = `
                    <div class="live-badge text-white"><span class="pulse-dot"></span> AI ACTIVE</div>
                    <video src="${data.video_url}" autoplay controls style="width: 100%; height: 100%; object-fit: cover;"></video>
                `;
            }

            // Trigger Slide-in Toast if threat found
            if (data.threat_found) {
                const toastBody = document.querySelector('#threatToast .toast-body');
                if (toastBody) {
                    toastBody.innerHTML = `<i class="fas fa-exclamation-triangle fa-fade me-2"></i> Alert: ${data.threat_details} detected! Email sent.`;
                    new bootstrap.Toast(document.getElementById('threatToast')).show();
                }
            } else {
                showMsg("Analysis Complete", "Video processed. No critical threats detected.", "success");
            }

            // Reload HUD Stats & Table immediately
            window.loadDashboardData();
        } else {
            showMsg("Analysis Error", data.detail || "Failed to process video.", "error");
        }
    } catch (error) {
        console.error("AI Analysis Failed:", error);
        showMsg("Connection Error", "Failed to connect to the AI engine. Ensure backend is running.", "error");
    } finally {
        // Reset button state
        btn.innerHTML = '<i class="fas fa-microchip me-2"></i> Run AI Analysis';
        btn.disabled = false;
    }
};

// 4. Render Chart.js
function updateChart(dataArray) {
    const canvas = document.getElementById('threatChart');
    if (!canvas) return; // Prevent error if not on dashboard page
    
    const ctx = canvas.getContext('2d');
    
    // Gradient Setup
    let gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(220, 53, 69, 0.5)'); 
    gradient.addColorStop(1, 'rgba(220, 53, 69, 0.0)');

    // Destroy existing chart to prevent overlap bugs
    if(threatChart) threatChart.destroy(); 

    threatChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Today'],
            datasets: [{
                label: 'Detections',
                data: dataArray,
                borderColor: '#dc3545',
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#dc3545',
                fill: true, 
                tension: 0.4 
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false, 
            plugins: { legend: { display: false } }, 
            scales: { 
                y: { beginAtZero: true },
                x: { grid: { display: false } } 
            } 
        }
    });
}
// Add inside document.addEventListener('DOMContentLoaded', () => { ... })
const forgotReqForm = document.getElementById('forgotRequestForm');
const forgotResetForm = document.getElementById('forgotResetForm');

if (forgotReqForm) {
    forgotReqForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleForgotRequest();
    });
}

if (forgotResetForm) {
    forgotResetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleForgotReset();
    });
}

// Logic to Request Reset OTP
async function handleForgotRequest() {
    const email = document.getElementById('forgotEmail').value;
    const btn = document.getElementById('forgotSendBtn');
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Dispatching...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        if (res.ok) {
            document.getElementById('forgotRequestForm').classList.add('d-none');
            document.getElementById('forgotResetForm').classList.remove('d-none');
            window.showMsg("OTP Sent", "Check your email for the reset code.", "success");
        } else {
            const data = await res.json();
            window.showMsg("Error", data.detail, "error");
        }
    } catch(e) {
        window.showMsg("Server Error", "Could not reach AI engine.", "error");
    } finally {
        btn.innerHTML = 'Send Reset OTP';
        btn.disabled = false;
    }
}

// Logic to Finalize Password Reset
async function handleForgotReset() {
    const email = document.getElementById('forgotEmail').value;
    const otp = document.getElementById('forgotOTP').value;
    const pass = document.getElementById('newPass').value;
    const btn = document.getElementById('resetBtn');

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, otp_code: otp, new_password: pass })
        });

        if (res.ok) {
            window.showMsg("Success", "Password updated. Redirecting to login...", "success");
            setTimeout(() => window.location.reload(), 2000);
        } else {
            const data = await res.json();
            window.showMsg("Reset Failed", data.detail, "error");
        }
    } catch(e) {
        window.showMsg("Error", "Server connection failed.", "error");
    } finally {
        btn.innerHTML = 'Update Password';
        btn.disabled = false;
    }
}