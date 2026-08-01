// const BACKEND_URL = window.BACKEND_URL || localStorage.getItem('BACKEND_URL') || "http://127.0.0.1:8000";

const BACKEND_URL = window.BACKEND_URL || localStorage.getItem('BACKEND_URL') || "https://asad0978.pythonanywhere.com";

// Modals Triggering
const authModal = document.getElementById('authModal');
const openAuthBtn = document.getElementById('openAuthBtn');
const getStartedBtn = document.getElementById('getStartedBtn');
const closeModalBtn = document.getElementById('closeModalBtn');
const loginSection = document.getElementById('loginSection');
const signupSection = document.getElementById('signupSection');

if (openAuthBtn) openAuthBtn.onclick = () => { authModal.classList.add('active'); loginSection.style.display = 'block'; signupSection.style.display = 'none'; }
if (getStartedBtn) getStartedBtn.onclick = () => { authModal.classList.add('active'); loginSection.style.display = 'block'; signupSection.style.display = 'none'; }
if (closeModalBtn) closeModalBtn.onclick = () => authModal.classList.remove('active');

if (document.getElementById('switchToSignup')) {
    document.getElementById('switchToSignup').onclick = (e) => {
        e.preventDefault();
        loginSection.style.display = 'none';
        signupSection.style.display = 'block';
    }
}
if (document.getElementById('switchToLogin')) {
    document.getElementById('switchToLogin').onclick = (e) => {
        e.preventDefault();
        signupSection.style.display = 'none';
        loginSection.style.display = 'block';
    }
}

// FAQ CODE 
document.querySelectorAll('.faq-item').forEach(item => {
    item.addEventListener('click', () => {
        // Dusre sabhi open FAQ items ko close karne ke liye:
        document.querySelectorAll('.faq-item').forEach(otherItem => {
            if (otherItem !== item) {
                otherItem.classList.remove('active');
            }
        });

        // Clicked element ko open/close toggle karne ke liye:
        item.classList.toggle('active');
    });
});


// ====================================================
// SECURE DIRECT-HIT LOGIN ENGINE
// ====================================================
window.executeForcedLogin = async function (event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const emailInput = document.getElementById('loginEmail');
    const passwordInput = document.getElementById('loginPassword');

    if (!emailInput || !passwordInput) {
        alert("Fields missing!");
        return false;
    }

    const emailValue = emailInput.value.trim();
    const passwordValue = passwordInput.value;

    if (!emailValue || !passwordValue) {
        alert("Email aur password enter karein.");
        return false;
    }

    try {
        const res = await fetch(`${BACKEND_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: emailValue,
                password: passwordValue
            })
        });

        const data = await res.json();
        console.log("LOGIN RESPONSE RECEIVED:", data);

        if (res.ok) {
            // User states save karein
            localStorage.setItem('userEmail', data.email || emailValue);
            localStorage.setItem('username', data.username || "User");

            // Absolute force redirection (Live Server proof)
            window.location.href = "dashboard.html";
        } else {
            alert(data.detail || "Ghalat credentials!");
        }
    } catch (err) {
        console.error("API Error:", err);
        alert("Server band hai! Backend terminal me check karein.");
    }

    return false;
};

// ====================================================
// AUTHENTICATION WORKING LOGIC (LOGIN & SIGNUP)
// ====================================================

// ====================================================
// TOTAL FORM BYPASS - LOGIN HANDLER
// ====================================================
const loginFormObj = document.getElementById('loginForm') || document.querySelector('form');

if (loginFormObj) {
    // 1. Pure form ke submit listener ko bind karke completely block karein
    loginFormObj.addEventListener('submit', function (e) {
        e.preventDefault();
        e.stopPropagation();
    });

    // 2. Button ke click listener par direct dynamic call lagayein
    const submitBtn = loginFormObj.querySelector('button[type="submit"]') || loginFormObj.querySelector('button');
    if (submitBtn) {
        // Iska type submit se badal kar direct button kar dete hain taake HTML reload mar hi na sakay
        submitBtn.setAttribute('type', 'button');

        submitBtn.addEventListener('click', async function (event) {
            event.preventDefault();
            event.stopPropagation();

            const emailInput = loginFormObj.querySelector('input[type="email"]');
            const passwordInput = loginFormObj.querySelector('input[type="password"]');

            if (!emailInput || !passwordInput) return;

            try {
                const res = await fetch(`${BACKEND_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: emailInput.value.trim(),
                        password: passwordInput.value
                    })
                });

                const data = await res.json();
                console.log("LOGIN RESPONSE RECEIVED:", data);

                if (res.ok) {
                    localStorage.setItem('userEmail', data.email || emailInput.value.trim());
                    localStorage.setItem('username', data.username || "User");

                    console.log("Redirecting now...");

                    // Live Server absolute folder redirection force rule
                    window.location.href = "/frontend/dashboard.html";
                } else {
                    alert(data.detail || "Ghalat email ya password!");
                }
            } catch (err) {
                console.error("Network flow failed:", err);
            }
        });
    }
}

// --- 2. SIGNUP HANDLING ---
const signupForm = document.querySelector('#signupForm') || document.querySelector('form[id*="signup"]');
if (signupForm) {
    signupForm.addEventListener('submit', async function (e) {
        e.preventDefault(); // Form reload rokne ke liye

        const nameField = signupForm.querySelector('input[type="text"]');
        const emailField = signupForm.querySelector('input[type="email"]');
        const passwordField = signupForm.querySelector('input[type="password"]');
        const errorDiv = document.getElementById('signupError') || (() => {
            let d = document.createElement('div'); d.style.color = 'red'; d.style.marginTop = '10px';
            signupForm.appendChild(d); return d;
        })();

        if (!emailField || !passwordField || !nameField) {
            console.error("Signup fields nahi milay!");
            return;
        }

        errorDiv.innerText = "Creating account...";
        errorDiv.style.color = "#2563eb";

        try {
            const res = await fetch(`${BACKEND_URL}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: nameField.value.trim(),
                    email: emailField.value.trim(),
                    password: passwordField.value
                })
            });

            const data = await res.json();

            if (res.ok) {
                errorDiv.innerText = "Account ban gaya! Ab login kijiye.";
                errorDiv.style.color = "green";
                signupForm.reset();
                alert("Account successfully created! Please login.");
            } else {
                errorDiv.innerText = data.detail || "Signup fail ho gaya.";
                errorDiv.style.color = "red";
            }
        } catch (err) {
            console.error(err);
            errorDiv.innerText = "Server error or network failure.";
            errorDiv.style.color = "red";
        }
    });
}

// Sidebar switching & dashboard components execution
const menuItems = document.querySelectorAll('.menu-item');
if (menuItems.length > 0) {
    menuItems.forEach(item => {
        item.addEventListener('click', function () {
            menuItems.forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.feature-panel').forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            document.getElementById(this.getAttribute('data-target')).classList.add('active');
        });
    });
}

// ====================================================
// 3. FEATURE WORKING LOGIC (BULLETPROOF SEND ENGINE)
// ====================================================
const loggedInEmail = localStorage.getItem('userEmail') || "guest@gmail.com";

const chatForm = document.getElementById('chatForm');
const sendChatBtn = document.getElementById('sendChatBtn');

async function handleChatSubmission(e) {
    if (e) e.preventDefault(); // Browser refresh block karein

    const input = document.getElementById('chatInput');
    const box = document.getElementById('chatBox');

    if (!input || !box || !input.value.trim()) return;

    const userMsg = input.value.trim();

    // User message UI par immediate display
    box.innerHTML += `<div class="user-msg" style="margin-bottom:8px;"><b>Aap:</b> ${userMsg}</div>`;
    input.value = ""; // Input clear
    box.scrollTop = box.scrollHeight;

    try {
        const res = await fetch(`${BACKEND_URL}/ai/study-chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: loggedInEmail,
                message: userMsg
            })
        });

        const data = await res.json();

        // --- PROFESSIONAL CUSTOM MARKDOWN PARSER FIX ---
        let rawText = data.response || "No response template received.";
        let cleanResponse = "";

        // Text ko lines me split karein taake har element sahi render ho
        let lines = rawText.split('\n');
        let inList = false;

        lines.forEach(line => {
            let trimmed = line.trim();
            if (!trimmed) return;

            // 1. Check for Sub-Headings (###)
            if (trimmed.startsWith('###')) {
                if (inList) { cleanResponse += '</ul>'; inList = false; }
                let headingText = trimmed.replace('###', '').trim();
                cleanResponse += `<h3 style="color: #1e3a8a; margin-top: 16px; margin-bottom: 8px; font-size: 1.15rem; font-weight: 600;">${headingText}</h3>`;
            }
            // 2. Check for Bullet Points (* or -)
            else if (trimmed.startsWith('*') || trimmed.startsWith('-')) {
                if (!inList) { cleanResponse += '<ul style="margin-top: 6px; margin-bottom: 8px; padding-left: 20px; list-style-type: square;">'; inList = true; }
                let bulletText = trimmed.substring(1).trim();

                // Bold elements parsing (**text**)
                bulletText = bulletText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                cleanResponse += `<li style="margin-bottom: 4px; line-height: 1.5; color: #334155;">${bulletText}</li>`;
            }
            // 3. Normal Paragraphs
            else {
                if (inList) { cleanResponse += '</ul>'; inList = false; }
                // Bold elements parsing (**text**)
                let textWithBold = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                cleanResponse += `<p style="margin-bottom: 8px; line-height: 1.6; color: #334155;">${textWithBold}</p>`;
            }
        });

        if (inList) { cleanResponse += '</ul>'; }

        // UI par display append karna
        box.innerHTML += `
                <div class="ai-msg" style="margin-top:12px; padding: 15px; background: #eff6ff; border-radius: 8px;">
                    <b style="color: #1e3a8a; display: block; margin-bottom: 8px; font-size: 1rem;">AI Study Assistant:</b> 
                    ${cleanResponse}
                </div>`;

        box.scrollTop = box.scrollHeight;

    } catch (err) {
        console.error("Chat flow catch error:", err);
        box.innerHTML += `<div class="error-msg" style="color:red; padding:10px;">Server connection lost!</div>`;
    }
}

// Dono hooks attach karein taake press enter ya button click dono par chale
if (chatForm) {
    chatForm.addEventListener('submit', handleChatSubmission);
}
if (sendChatBtn) {
    sendChatBtn.addEventListener('click', handleChatSubmission);
}

// Summarizer Handler
const summarizeBtn = document.getElementById('summarizeBtn');
if (summarizeBtn) {
    summarizeBtn.addEventListener('click', async function () {
        const fileInput = document.getElementById('summaryFileInput');
        const resultDiv = document.getElementById('summaryResult');

        if (!fileInput.files || fileInput.files.length === 0) {
            alert("Meharbani karke pehle ek file select karein.");
            return;
        }

        const file = fileInput.files[0];
        resultDiv.innerHTML = "<b>AI processing aur file read ho rahi hai... Meharbani karke intizar karein.</b>";

        const formData = new FormData();
        formData.append("file", file);
        formData.append("email", localStorage.getItem('userEmail') || "guest@gmail.com");

        try {
            const res = await fetch(`${BACKEND_URL}/ai/summarize`, {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.ok) {
                let rawText = data.response || "No summary text returned.";
                let cleanSummary = "";

                let lines = rawText.split('\n');
                let inList = false;

                lines.forEach(line => {
                    let trimmed = line.trim();
                    if (!trimmed) return;

                    // 1. FIX: Agar line * se shuru ho aur end ** par ho (Heading detection)
                    if (trimmed.startsWith('*') && trimmed.endsWith('**')) {
                        if (inList) { cleanSummary += '</ul>'; inList = false; }

                        // Saare asterisks saaf karke clean heading text nikalna
                        let headingText = trimmed.replace(/\*/g, '').trim();
                        cleanSummary += `<h3 style="color: #1e3a8a; margin-top: 18px; margin-bottom: 8px; font-size: 1.15rem; font-weight: 600;">${headingText}</h3>`;
                    }
                    // 2. Standard Markdown Headings Check (###)
                    else if (trimmed.startsWith('###')) {
                        if (inList) { cleanSummary += '</ul>'; inList = false; }
                        let headingText = trimmed.replace('###', '').trim();
                        cleanSummary += `<h3 style="color: #1e3a8a; margin-top: 18px; margin-bottom: 8px; font-size: 1.15rem; font-weight: 600;">${headingText}</h3>`;
                    }
                    // 3. Clean Bullet Points Handling
                    else if (trimmed.startsWith('*') || trimmed.startsWith('-')) {
                        if (!inList) { cleanSummary += '<ul style="margin-top: 6px; margin-bottom: 6px; padding-left: 20px; list-style-type: square;">'; inList = true; }
                        let bulletText = trimmed.substring(1).trim();

                        // Bold parsing fix (**text**)
                        bulletText = bulletText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                        cleanSummary += `<li style="margin-bottom: 5px; line-height: 1.5; color: #334155;">${bulletText}</li>`;
                    }
                    // 4. Regular Paragraphs
                    else {
                        if (inList) { cleanSummary += '</ul>'; inList = false; }
                        // Bold parsing fix (**text**)
                        let textWithBold = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                        cleanSummary += `<p style="margin-bottom: 8px; line-height: 1.5; color: #334155;">${textWithBold}</p>`;
                    }
                });

                if (inList) { cleanSummary += '</ul>'; }

                resultDiv.innerHTML = `<div style="padding: 5px; background: #f8fafc; border-radius: 6px;">${cleanSummary}</div>`;

            } else {
                resultDiv.innerHTML = `<span style="color:red;">Error: ${data.detail || "Summary generate nahi ho saki."}</span>`;
            }
        } catch (error) {
            console.error("Summarizer sync error:", error);
            resultDiv.innerHTML = `<span style="color:red;">Backend connection fail ho gaya hai.</span>`;
        }
    });
}

// ====================================================
// QUIZ GENERATOR WORKING LOGIC
// ====================================================
const quizBtn = document.getElementById('quizBtn');
if (quizBtn) {
    quizBtn.addEventListener('click', async function () {
        const topicInput = document.getElementById('quizTopicInput');
        const resultDiv = document.getElementById('quizResult');
        const topic = topicInput.value.trim();

        if (!topic) {
            alert("Meharbani karke pehle koi topic enter karein.");
            return;
        }

        resultDiv.innerHTML = "<b>AI aapke liye real-time MCQs test taiyar kar raha hai... Please wait.</b>";

        try {
            const res = await fetch(`${BACKEND_URL}/ai/generate-quiz`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: topic,
                    email: localStorage.getItem('userEmail') || "guest@gmail.com"
                })
            });

            const data = await res.json();

            if (res.ok && data.questions && data.questions.length > 0) {
                let quizHTML = `<form id="interactiveQuizForm" style="margin-top:15px;">`;

                data.questions.forEach((q, index) => {
                    quizHTML += `
                        <div class="quiz-question-block" style="margin-bottom: 20px; background: #fff; padding: 15px; border-radius: 8px; border-left: 4px solid #2563eb;">
                            <p style="font-weight: 600; margin-bottom: 10px;">Q${index + 1}: ${q.question}</p>
                            <label style="display:block; margin: 6px 0; cursor:pointer;"><input type="radio" name="q_${index}" value="a" required> A) ${q.a}</label>
                            <label style="display:block; margin: 6px 0; cursor:pointer;"><input type="radio" name="q_${index}" value="b"> B) ${q.b}</label>
                            <label style="display:block; margin: 6px 0; cursor:pointer;"><input type="radio" name="q_${index}" value="c"> C) ${q.c}</label>
                            <label style="display:block; margin: 6px 0; cursor:pointer;"><input type="radio" name="q_${index}" value="d"> D) ${q.d}</label>
                            <input type="hidden" id="ans_${index}" value="${q.answer}">
                        </div>
                    `;
                });

                quizHTML += `
                    <button type="submit" class="btn-feature-action" style="background:#10b981; margin-top:10px;">Submit Quiz Answers</button>
                    </form>
                    <div id="quizScoreResult" style="margin-top:15px; font-size:18px; font-weight:bold; color:#1e3a8a;"></div>
                `;

                resultDiv.innerHTML = quizHTML;

                // Form Submit Score Evaluation Handler
                document.getElementById('interactiveQuizForm').addEventListener('submit', function (e) {
                    e.preventDefault();
                    let score = 0;
                    const total = data.questions.length;

                    data.questions.forEach((q, index) => {
                        const selectedOption = document.querySelector(`input[name="q_${index}"]:checked`).value;
                        const correctOption = document.getElementById(`ans_${index}`).value.toLowerCase().trim();

                        if (selectedOption === correctOption) {
                            score++;
                        }
                    });

                    document.getElementById('quizScoreResult').innerHTML = `Aapka Score: ${score} / ${total} 🎉`;
                    alert(`Quiz finished! You scored ${score}/${total}`);
                });

            } else {
                resultDiv.innerHTML = `<span style="color:red;">Error: Quiz generate nahi ho saka. Dobara koshish karein.</span>`;
            }
        } catch (err) {
            resultDiv.innerHTML = `<span style="color:red;">Server connection fail ho gaya hai.</span>`;
        }
    });
}


// ====================================================
// MULTI-UPLOAD AND SUMMARIZE LOGIC CONTROLLER
// ====================================================

// Files ka data save rakhne ke liye global array
let currentSelectedFiles = [];

function handleDashMultiSelect(inputElement) {
    const filesListContainer = document.getElementById('dashFilesList');
    const summaryActionBlock = document.getElementById('summaryActionBlock');
    const cardsWrapper = document.getElementById('dynamicSummaryCardsWrapper');

    filesListContainer.innerHTML = ''; // Clear previous UI
    if (cardsWrapper) cardsWrapper.innerHTML = ''; // Purane cards saaf karne ke liye

    currentSelectedFiles = Array.from(inputElement.files);

    if (currentSelectedFiles.length === 0) {
        summaryActionBlock.style.display = 'none';
        return;
    }

    // Show the "Summarize All Uploaded Docs" button
    summaryActionBlock.style.display = 'block';

    currentSelectedFiles.forEach((file) => {
        const fileSizeKB = (file.size / 1024).toFixed(1);
        const fileChip = document.createElement('div');
        fileChip.className = 'dash-file-chip';
        fileChip.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>📄</span>
                <strong>${file.name}</strong> 
                <span style="color: #94a3b8; font-size: 0.8rem;">(${fileSizeKB} KB)</span>
            </div>
            <span style="color: #2563eb; font-weight: bold; font-size: 0.8rem; background: #dbeafe; padding: 2px 8px; border-radius: 4px;">Selected</span>
        `;
        filesListContainer.appendChild(fileChip);
    });
}

// ====================================================
// UPDATED REAL-TIME MULTI-FILE API EXPLANATION ENGINE
// ====================================================

async function generateMultiSummary() {
    const cardsWrapper = document.getElementById('dynamicSummaryCardsWrapper');
    
    if (!cardsWrapper) {
        console.error("HTML mein id='dynamicSummaryCardsWrapper' missing hai!");
        return;
    }
    
    cardsWrapper.innerHTML = ''; 

    if (currentSelectedFiles.length === 0) {
        alert("Kindly select files first!");
        return;
    }

    for (let index = 0; index < currentSelectedFiles.length; index++) {
        const file = currentSelectedFiles[index];
        
        const card = document.createElement('div');
        card.className = 'single-doc-summary-card';

        // Stacked top header & bottom full-width content
        card.innerHTML = `
            <div class="doc-summary-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.1rem;">📄</span>
                    <strong style="color: #1e293b;">Document [${index + 1}]: ${file.name}</strong>
                </div>
                <span id="status-badge-${index}" style="color: #d97706; background: #fef3c7; padding: 5px 12px; border-radius: 6px; font-weight: 600;">⚡ AI Analyzing...</span>
            </div>
            
            <div class="doc-summary-body">
                <div id="loader-container-${index}" style="display: flex; align-items: center; gap: 10px; color: #64748b; padding: 10px 0;">
                    <div class="spinner-loader" style="border: 3px solid #f3f3f3; border-top: 3px solid #2563eb; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite;"></div>
                    <p style="margin:0; font-size:0.95rem;">Backend AI extracting and generating explanation...</p>
                </div>
                
                <div id="content-area-${index}" style="display: none;">
                    <h4 style="margin: 0 0 16px 0; color: #0f172a; font-size: 1.15rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                        <span>🤖</span> AI Detailed English Explanation
                    </h4>
                    
                    <div id="ai-response-text-${index}" class="markdown-output-content"></div>
                </div>
            </div>
        `;
        cardsWrapper.appendChild(card);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('email', localStorage.getItem('userEmail') || 'guest@gmail.com');

        try {
            const apiBase = typeof BACKEND_URL !== 'undefined' ? BACKEND_URL : "http://127.0.0.1:8000";
            const response = await fetch(`${apiBase}/api/multi-upload-explain`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error("API Call Failed");

            const result = await response.json();
            const realAiExplanation = result.explanation || "Could not retrieve explanation.";
            
            document.getElementById(`loader-container-${index}`).style.display = 'none';
            document.getElementById(`content-area-${index}`).style.display = 'block';
            
            const badge = document.getElementById(`status-badge-${index}`);
            badge.style.color = '#2563eb';
            badge.style.background = '#dbeafe';
            badge.innerText = '✍ AI Typing...';

            await streamTextOutput(`ai-response-text-${index}`, realAiExplanation);

            badge.style.color = '#16a34a';
            badge.style.background = '#dcfce7';
            badge.innerText = '✓ Explained';

        } catch (error) {
            console.error("Error fetching explanation:", error);
            document.getElementById(`loader-container-${index}`).style.display = 'none';
            document.getElementById(`content-area-${index}`).style.display = 'block';
            
            const badge = document.getElementById(`status-badge-${index}`);
            badge.style.color = '#dc2626';
            badge.style.background = '#fee2e2';
            badge.innerText = '✕ Failed';

            document.getElementById(`ai-response-text-${index}`).innerHTML = 
                `<span style="color: #dc2626;">Failed to process document. Please check server connection.</span>`;
        }
    }
}

// Stream Function Optimization with Markdown Fallback
function streamTextOutput(elementId, fullText) {
    return new Promise((resolve) => {
        const targetElement = document.getElementById(elementId);
        if (!targetElement) { resolve(); return; }

        let currentWordIndex = 0;
        const wordsArray = fullText.split(" ");
        let progressiveText = ""; 
        
        function printNextWord() {
            if (currentWordIndex < wordsArray.length) {
                progressiveText += (currentWordIndex === 0 ? "" : " ") + wordsArray[currentWordIndex];
                
                if (typeof marked !== 'undefined') {
                    targetElement.innerHTML = marked.parse(progressiveText);
                } else {
                    let formatted = progressiveText
                        .replace(/^### (.*$)/gim, '<h3 style="color:#1e3a8a; margin-top:12px;">$1</h3>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\n/g, '<br>');
                    targetElement.innerHTML = formatted;
                }
                
                currentWordIndex++;
                setTimeout(printNextWord, 15);
            } else {
                resolve(); 
            }
        }
        printNextWord();
    });
}


// =====================================================================
// FEATURE: REAL-TIME AI CODE EXPLAINER CONTROLLER
// =====================================================================

async function generateCodeExplanation() {
    // 1. DOM Elements
    const codeContent = document.getElementById('rawCodeInput').value;
    const selectedLanguage = document.getElementById('codeLanguageSelect').value;
    const outputBlock = document.getElementById('codeExplanationOutputBlock');
    const responseContainer = document.getElementById('code-ai-response-text');
    const badge = document.getElementById('code-status-badge');
    
    // Quick Language Selection from Right Side
    const explanationLanguage = document.getElementById('explanationLanguageSelect').value;

    // 2. Input Validation
    if (!codeContent.trim()) {
        alert("Please paste your source code first!");
        return;
    }

    // 3. Setup UI Loading State
    responseContainer.innerHTML = `
        <div id="code-internal-loader" style="display: flex; align-items: center; gap: 10px; color: #64748b; font-family: sans-serif; padding: 5px 0;">
            <div class="spinner-loader" style="border: 3px solid #f3f3f3; border-top: 3px solid #2563eb; border-radius: 50%; width: 18px; height: 18px; animation: spin 1s linear infinite;"></div>
            <p style="margin:0; font-size:0.95rem;">AI Software Engineer is translating explanation to ${explanationLanguage}...</p>
        </div>
    `;
    outputBlock.style.display = 'block';
    
    badge.style.color = '#d97706';
    badge.style.background = '#fef3c7';
    badge.innerText = '⚡ AI Translating...';

    // 4. API Payload
    const payload = {
        code: codeContent,
        language: selectedLanguage,
        target_language: explanationLanguage,
        email: "guest@gmail.com" 
    };

    try {
        const backendPort = "8000"; 
        const response = await fetch(`http://127.0.0.1:${backendPort}/api/explain-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("API Route Connection Failure");

        const result = await response.json();
        const aiExplanation = result.explanation || "No explanation text returned.";

        // Clear Loader before starting typing stream
        responseContainer.innerHTML = "";

        badge.style.color = '#2563eb';
        badge.style.background = '#dbeafe';
        badge.innerText = '✍ AI Typing...';

        // 5. Trigger Real-Time Typewriter Typing Stream
        await streamCodeExplanationText('code-ai-response-text', aiExplanation);

        // Success State Update
        badge.style.color = '#16a34a';
        badge.style.background = '#dcfce7';
        badge.innerText = '✓ Code Explained';

    } catch (error) {
        console.error("Code Analysis Pipeline Failed:", error);
        
        badge.style.color = '#dc2626';
        badge.style.background = '#fee2e2';
        badge.innerText = '✕ Failed';
        
        responseContainer.innerHTML = `
            <span style="color: #dc2626; font-weight: 500;">
                Execution Failed: ${error.message}. Please verify if your FastAPI server (Port 8000) is running.
            </span>
        `;
    }
}

// =====================================================================
// FEATURE: IMAGE & DIAGRAM EXPLAINER CONTROLLER (FULLY FIXED)
// =====================================================================

let selectedImageBase64 = null;

// Initialize Drag & Drop Events directly on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('imageDropzone');
    const fileInput = document.getElementById('imageFileInput');

    if (dropzone && fileInput) {
        // 1. Click to trigger file picker
        dropzone.addEventListener('click', (e) => {
            // Agar remove/change button par click hua ho toh file picker reopen na ho
            if (e.target.classList.contains('btn-remove-img')) return;
            fileInput.click();
        });

        // 2. Drag Over Effect
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-active');
        });

        // 3. Drag Leave Effect
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-active');
        });

        // 4. File Drop Action
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-active');

            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleImagePreview({ target: fileInput });
            }
        });
    }
});


// 1. Handle File Selection & Preview
function handleImagePreview(event) {
    const file = event.target.files ? event.target.files[0] : null;
    if (!file) return;

    // File Size Check (10MB)
    if (file.size > 10 * 1024 * 1024) {
        alert("File size exceeds 10MB limit! Please upload a smaller image.");
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        selectedImageBase64 = e.target.result;

        const previewImg = document.getElementById('imagePreview');
        const dropzonePrompt = document.getElementById('dropzonePrompt');
        const previewContainer = document.getElementById('imagePreviewContainer');

        if (previewImg) previewImg.src = selectedImageBase64;
        if (dropzonePrompt) dropzonePrompt.style.display = 'none';
        if (previewContainer) previewContainer.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

// 2. Remove / Reset Selected Image
function removeImagePreview(event) {
    if (event) event.stopPropagation(); // Stop Dropzone click re-triggering
    selectedImageBase64 = null;

    const fileInput = document.getElementById('imageFileInput');
    const previewImg = document.getElementById('imagePreview');
    const previewContainer = document.getElementById('imagePreviewContainer');
    const dropzonePrompt = document.getElementById('dropzonePrompt');

    if (fileInput) fileInput.value = "";
    if (previewImg) previewImg.src = "";
    if (previewContainer) previewContainer.style.display = 'none';
    if (dropzonePrompt) dropzonePrompt.style.display = 'block';
}

// 3. API Dispatcher & Streaming Engine
async function generateImageExplanation() {
    const outputBlock = document.getElementById('imageExplanationOutputBlock');
    const responseContainer = document.getElementById('image-ai-response-text');
    const badge = document.getElementById('image-status-badge');
    const langSelect = document.getElementById('imageLanguageSelect');

    if (!responseContainer) {
        alert("Error: Output container element not found in HTML!");
        return;
    }

    if (!selectedImageBase64) {
        alert("Please select or drop an image/diagram first!");
        return;
    }

    const targetLanguage = langSelect ? langSelect.value : "English";
    const promptInput = document.getElementById('imageCustomPrompt');
    const userPrompt = promptInput ? promptInput.value.trim() : "";

    // Reset UI to Loading State
    if (outputBlock) outputBlock.style.display = 'block';

    responseContainer.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: #64748b; padding: 10px 0;">
            <div class="spinner-loader" style="border: 3px solid #f3f3f3; border-top: 3px solid #2563eb; border-radius: 50%; width: 18px; height: 18px; animation: spin 1s linear infinite;"></div>
            <p style="margin:0; font-size:0.95rem;">AI Vision Engine is analyzing diagram in ${targetLanguage}...</p>
        </div>
    `;

    if (badge) {
        badge.style.color = '#d97706';
        badge.style.background = '#fef3c7';
        badge.innerText = '⚡ AI Analyzing Image...';
    }

    const payload = {
        image_base64: selectedImageBase64,
        target_language: targetLanguage,
        custom_prompt: userPrompt,
        email: localStorage.getItem('userEmail') || "guest@gmail.com"
    };

    try {
        const apiBase = typeof BACKEND_URL !== 'undefined' ? BACKEND_URL : "http://127.0.0.1:8000";

        const response = await fetch(`${apiBase}/api/explain-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            let errorMsg = "Backend connection failure.";
            try {
                const errData = await response.json();
                errorMsg = errData.detail || errorMsg;
            } catch (e) { }
            throw new Error(errorMsg);
        }

        const result = await response.json();
        const aiExplanation = result.explanation || "No explanation returned from server.";

        responseContainer.innerHTML = "";

        if (badge) {
            badge.style.color = '#2563eb';
            badge.style.background = '#dbeafe';
            badge.innerText = '✍ AI Writing Explanation...';
        }

        // Safe Fallback for Typing Effect Function
        if (typeof streamCodeExplanationText === 'function') {
            await streamCodeExplanationText('image-ai-response-text', aiExplanation);
        } else {
            if (typeof marked !== 'undefined') {
                responseContainer.innerHTML = marked.parse(aiExplanation);
            } else {
                responseContainer.innerHTML = aiExplanation.replace(/\n/g, '<br>');
            }
        }

        if (badge) {
            badge.style.color = '#16a34a';
            badge.style.background = '#dcfce7';
            badge.innerText = '✓ Image Explained';
        }

    } catch (error) {
        console.error("Image Analysis Pipeline Failed:", error);

        if (badge) {
            badge.style.color = '#dc2626';
            badge.style.background = '#fee2e2';
            badge.innerText = '✕ Failed';
        }

        responseContainer.innerHTML = `
            <span style="color: #dc2626; font-weight: 500;">
                Execution Failed: ${error.message}. Please verify if your FastAPI backend server is running on port 8000.
            </span>
        `;
    }
}

// =====================================================================
// GLOBAL NAVIGATION CONTROLLER (FIXED & ROBUST)
// =====================================================================
document.addEventListener('DOMContentLoaded', () => {
    
    // Add Click listener to all menu items with data-target
    const menuItems = document.querySelectorAll('[data-target]');

    menuItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('data-target');
            console.log(`[Navigation] Switch requested for ID: ${targetId}`);

            if (!targetId) return;

            // 1. Hide all feature panels
            const allPanels = document.querySelectorAll('.feature-panel');
            allPanels.forEach(panel => {
                panel.style.display = 'none';
            });

            // 2. Remove 'active' class from all menu items
            document.querySelectorAll('.menu-item, .nav-item').forEach(el => {
                el.classList.remove('active');
            });

            // 3. Highlight current menu item
            this.classList.add('active');

            // 4. Reveal targeted panel
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) {
                targetPanel.style.display = 'block';
                console.log(`[Navigation] Successfully displayed: #${targetId}`);
            } else {
                console.error(`[Navigation Error] Could not find HTML element with ID: #${targetId}`);
            }
        });
    });

});

// =====================================================================
// GUARANTEED PANEL SWITCHER FUNCTION (Direct & Event-driven)
// =====================================================================

function switchPanel(targetId) {
    console.log("[Panel Switcher] Attempting to show panel:", targetId);

    // 1. Check if target element exists
    const targetElement = document.getElementById(targetId);
    if (!targetElement) {
        console.error(`[Panel Error] ID "${targetId}" wala HTML section nahi mila!`);
        return;
    }

    // 2. Hide ALL feature panels strictly using setProperty
    const allPanels = document.querySelectorAll('.feature-panel, section[id$="panel"]');
    allPanels.forEach(panel => {
        panel.style.setProperty('display', 'none', 'important');
    });

    // 3. Remove 'active' highlight class from all sidebar links/items
    document.querySelectorAll('.menu-item, .nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // 4. Force reveal the target panel
    targetElement.style.setProperty('display', 'block', 'important');

    // 5. Ensure internal dashboard containers are visible
    const internalCards = targetElement.querySelectorAll('.dashboard-panel, .image-to-text-card');
    internalCards.forEach(card => {
        card.style.setProperty('display', 'block', 'important');
    });

    // 6. Highlight selected sidebar item
    const activeMenuItem = document.querySelector(`[data-target="${targetId}"]`);
    if (activeMenuItem) {
        activeMenuItem.classList.add('active');
    }

    console.log(`[Panel Switcher] Successfully activated #${targetId}`);
}

// Global Event Listener (Fallback)
document.addEventListener('DOMContentLoaded', () => {
    // Add Click Binding to all items having data-target
    document.querySelectorAll('[data-target]').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            if (targetId) {
                switchPanel(targetId);
            }
        });
    });
});


// =====================================================================
// SYSTEM: MARKDOWN STREAM TEXT OUTPUT ENGINE
// =====================================================================
function streamCodeExplanationText(elementId, fullText) {
    return new Promise((resolve) => {
        const targetElement = document.getElementById(elementId);
        let currentWordIndex = 0;
        const wordsArray = fullText.split(" ");
        let progressiveText = ""; 
        
        function printNextWord() {
            if (currentWordIndex < wordsArray.length) {
                progressiveText += (currentWordIndex === 0 ? "" : " ") + wordsArray[currentWordIndex];
                
                // Real-time markdown parser compilation check
                if (typeof marked !== 'undefined') {
                    targetElement.innerHTML = marked.parse(progressiveText);
                } else {
                    targetElement.innerText = progressiveText; 
                }
                
                currentWordIndex++;
                setTimeout(printNextWord, 12); // Rendering speed delay
            } else {
                resolve(); 
            }
        }
        printNextWord();
    });
}

// ====================================================
// THE ULTIMATE ANTI-RELOAD GLOBAL LOGIN FUNCTION
// ====================================================
window.executeForcedLogin = async function (event) {
    // Browser ke default reload behavior ko block karna
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const emailInput = document.getElementById('loginEmail');
    const passwordInput = document.getElementById('loginPassword');

    if (!emailInput || !passwordInput) {
        console.error("Input DOM fields missing!");
        return false;
    }

    const emailValue = emailInput.value.trim();
    const passwordValue = passwordInput.value;

    if (!emailValue || !passwordValue) {
        alert("Please enter both email and password.");
        return false;
    }

    // Backend port fallback validation
    const targetBackend = (typeof BACKEND_URL !== 'undefined') ? BACKEND_URL : "http://127.0.0.1:8000";

    try {
        const res = await fetch(`${targetBackend}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: emailValue,
                password: passwordValue
            })
        });

        const data = await res.json();
        console.log("FINAL REDIRECTION TRACE:", data);

        if (res.ok) {
            // Local Session Store parameters
            localStorage.setItem('userEmail', data.email || emailValue);
            localStorage.setItem('username', data.username || "User");

            console.log("Redirecting now to dashboard.html...");

            // Hard redirection jo browser ko force karegi dashboard open karne ke liye
            window.location.replace("dashboard.html");
        } else {
            alert(data.detail || "Ghalat email ya password!");
        }
    } catch (err) {
        console.error("Redirection Network Exception:", err);
        alert("Server validation fail! Check if backend is running.");
    }

    return false;
};

// ====================================================
// FORCED DIRECT OVERRIDE TO INDEX.HTML
// ====================================================
function initActiveUserProfileAndLogout() {
    const currentLoggedInEmail = localStorage.getItem('userEmail');

    const avatarSlot = document.getElementById('userAvatarSlot');
    const nameSlot = document.getElementById('sidebarUserName');
    const emailSlot = document.getElementById('sidebarUserEmail');

    if (currentLoggedInEmail && (avatarSlot || nameSlot || emailSlot)) {
        let dynamicName = currentLoggedInEmail.split('@')[0];
        dynamicName = dynamicName.charAt(0).toUpperCase() + dynamicName.slice(1);
        const firstLetter = dynamicName.charAt(0).toUpperCase();

        if (avatarSlot) avatarSlot.innerText = firstLetter;
        if (nameSlot) nameSlot.innerText = dynamicName;
        if (emailSlot) emailSlot.innerText = currentLoggedInEmail;
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        // Purane handlers ko kill karne ke liye direct event listener assignment
        logoutBtn.onclick = function (e) {
            e.preventDefault();
            e.stopPropagation();

            localStorage.clear();
            alert("Aap kamiyabi se logout ho chuke hain.");

            // Automatic location matching for Port 5500 -> index.html
            let path = window.location.pathname;
            let dir = path.substring(0, path.lastIndexOf('/'));
            window.location.href = window.location.origin + dir + "/index.html";
        };
        console.log("Logout handler strictly locked onto index.html!");
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initActiveUserProfileAndLogout);
} else {
    initActiveUserProfileAndLogout();
}



// =====================================================================
// MASTER SIDEBAR NAVIGATION CONTROLLER (FIXED FOR CODE EXPLAINER)
// =====================================================================
document.addEventListener("DOMContentLoaded", function() {
    const menuItems = document.querySelectorAll('.menu-item');

    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            // 1. Saare menu items se 'active' class remove karein aur clicked wale par lagayein
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');

            // 2. Target ID extract karein (e.g., "Codeexplainpanel")
            const targetId = this.getAttribute('data-target');
            console.log("Navigating to panel ID:", targetId); // Debugging line browser console ke liye

            if (!targetId) return;

            // 3. SAFE HIDEOUT: Saare possible feature panels ko hide karein
            // Hum .feature-panel aur .dashboard-panel dono ko target kar rahe hain taake safe side rahein
            const allPanels = document.querySelectorAll('.feature-panel, .dashboard-panel, section[id]');
            allPanels.forEach(panel => {
                // Sirf un sections ko hide karein jo actual features hain
                if (panel.id && panel.id.toLowerCase().includes('panel')) {
                    panel.style.display = 'none';
                }
            });

            // 4. Targeted Panel ko unique show karein
            const activePanel = document.getElementById(targetId);
            if (activePanel) {
                activePanel.style.display = 'block';
                console.log("Successfully displayed panel:", targetId);
            } else {
                console.error(`HTML mein id="${targetId}" ka koi element nahi mila!`);
            }
        });
    });
});



// =====================================================================
// ISOLATED PATCH: ONLY FOR IMAGE TO TEXT (Zero Interference)
// =====================================================================
(function () {
    let imgBase64Store = null;

    // Helper: Preview Handle
    window.handleImagePreview = function(event) {
        const file = event.target.files ? event.target.files[0] : null;
        if (!file) return;

        if (file.size > 10 * 1024 * 1024) {
            alert("File limit 10MB se zyada hai!");
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            imgBase64Store = e.target.result;
            const previewImg = document.getElementById('imagePreview');
            const dropzonePrompt = document.getElementById('dropzonePrompt');
            const previewContainer = document.getElementById('imagePreviewContainer');

            if (previewImg) previewImg.src = imgBase64Store;
            if (dropzonePrompt) dropzonePrompt.style.display = 'none';
            if (previewContainer) previewContainer.style.display = 'flex';
        };
        reader.readAsDataURL(file);
    };

    // Helper: Remove Preview
    window.removeImagePreview = function(event) {
        if (event) event.stopPropagation();
        imgBase64Store = null;

        const fileInput = document.getElementById('imageFileInput');
        const previewImg = document.getElementById('imagePreview');
        const previewContainer = document.getElementById('imagePreviewContainer');
        const dropzonePrompt = document.getElementById('dropzonePrompt');

        if (fileInput) fileInput.value = "";
        if (previewImg) previewImg.src = "";
        if (previewContainer) previewContainer.style.display = 'none';
        if (dropzonePrompt) dropzonePrompt.style.display = 'block';
    };

    // Helper: Generate API Explanation
    window.generateImageExplanation = async function() {
        const outputBlock = document.getElementById('imageExplanationOutputBlock');
        const responseContainer = document.getElementById('image-ai-response-text');
        const badge = document.getElementById('image-status-badge');
        const langSelect = document.getElementById('imageLanguageSelect');
        const promptInput = document.getElementById('imageCustomPrompt');

        if (!imgBase64Store) {
            alert("Pehle image select karein!");
            return;
        }

        const targetLanguage = langSelect ? langSelect.value : "English";
        const userPrompt = promptInput ? promptInput.value.trim() : "";

        if (outputBlock) outputBlock.style.display = 'block';
        if (responseContainer) responseContainer.innerHTML = "<p style='color:#64748b;'>Analyzing image content...</p>";

        if (badge) {
            badge.innerText = '⚡ Processing...';
            badge.style.background = '#fef3c7';
            badge.style.color = '#d97706';
        }

        try {
            const apiBase = (typeof BACKEND_URL !== 'undefined') ? BACKEND_URL : "http://127.0.0.1:8000";
            const response = await fetch(apiBase + "/api/explain-image", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_base64: imgBase64Store,
                    target_language: targetLanguage,
                    custom_prompt: userPrompt,
                    email: localStorage.getItem('userEmail') || "guest@gmail.com"
                })
            });

            if (!response.ok) throw new Error("Server Request Failed");

            const data = await response.json();
            const textOutput = data.explanation || "No text received.";

            if (typeof streamCodeExplanationText === 'function') {
                await streamCodeExplanationText('image-ai-response-text', textOutput);
            } else if (typeof marked !== 'undefined') {
                responseContainer.innerHTML = marked.parse(textOutput);
            } else {
                responseContainer.innerHTML = textOutput.replace(/\n/g, '<br>');
            }

            if (badge) {
                badge.innerText = '✓ Completed';
                badge.style.background = '#dcfce7';
                badge.style.color = '#16a34a';
            }

        } catch (err) {
            if (responseContainer) {
                responseContainer.innerHTML = "<span style='color:red;'>Error: " + err.message + "</span>";
            }
            if (badge) badge.innerText = '✕ Failed';
        }
    };

    // Dedicated Fix for Image to Text Click
document.addEventListener('click', function(e) {
    const menuItem = e.target.closest('[data-target="imagetotextpanel"]');
    if (menuItem) {
        // 1. Saare baqi panels ko hide karein
        const allPanels = document.querySelectorAll('.feature-panel, section[id], div[id*="panel"]');
        allPanels.forEach(p => {
            if (p.id && p.id !== 'imagetotextpanel') {
                p.style.setProperty('display', 'none', 'important');
            }
        });

        // 2. Active class ko sidebar links se reset karein
        document.querySelectorAll('.menu-item, .nav-item').forEach(item => item.classList.remove('active'));
        menuItem.classList.add('active');

        // 3. Image to Text panel ko force display karein
        const imagePanel = document.getElementById('imagetotextpanel');
        if (imagePanel) {
            imagePanel.style.setProperty('display', 'block', 'important');
            const innerCard = imagePanel.querySelector('.image-to-text-card, .dashboard-panel');
            if (innerCard) {
                innerCard.style.setProperty('display', 'block', 'important');
            }
        }
    }
});

    // Isolated Event Binding (Only for Image Dropzone & Triggering Panel)
    window.addEventListener('DOMContentLoaded', () => {
        const dropzone = document.getElementById('imageDropzone');
        const fileInput = document.getElementById('imageFileInput');

        if (dropzone && fileInput) {
            dropzone.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn-remove-img')) return;
                fileInput.click();
            });

            dropzone.addEventListener('dragover', (e) => e.preventDefault());

            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    fileInput.files = e.dataTransfer.files;
                    window.handleImagePreview({ target: fileInput });
                }
            });
        }
    });
})();