"""
HTML pages for Terms of Service and Privacy Policy compliance required by Discord Developer Portal.
Serves mobile-friendly HTML endpoints at /terms and /privacy strictly using #000543, white, Horizon font, and Sortling Mascot icon.
"""

COMMON_STYLE = """
<style>
    @font-face {
        font-family: 'Horizon';
        font-style: normal;
        font-weight: 400;
        src: url('data:font/woff;base64,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') format('woff');
    }
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #000543;
        --card-bg: rgba(255, 255, 255, 0.04);
        --border: rgba(255, 255, 255, 0.18);
        --text: #ffffff;
        --text-muted: rgba(255, 255, 255, 0.75);
    }
    * {
        box-sizing: border-box;
    }
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #000543;
        color: #ffffff;
        margin: 0;
        padding: 40px 20px;
        line-height: 1.6;
        min-height: 100vh;
    }
    .container {
        max-width: 820px;
        margin: 0 auto;
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 44px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    }
    .brand-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding-bottom: 24px;
        border-bottom: 1px solid var(--border);
        margin-bottom: 28px;
    }
    .brand-icon {
        width: 52px;
        height: 52px;
        background: #ffffff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        flex-shrink: 0;
    }
    .brand-icon img {
        width: 38px;
        height: 38px;
        object-fit: contain;
    }
    .brand-title-group {
        display: flex;
        flex-direction: column;
    }
    .brand-name {
        font-family: 'Horizon', 'Inter', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 8px;
        letter-spacing: 1px;
    }
    .discord-badge {
        font-family: 'Inter', sans-serif;
        background: #ffffff;
        color: #000543;
        font-size: 0.65rem;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }
    .brand-subtitle {
        font-size: 0.9rem;
        color: var(--text-muted);
    }
    h1 {
        font-family: 'Horizon', 'Inter', sans-serif;
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0 0 20px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        letter-spacing: 0.5px;
    }
    h2 {
        font-family: 'Horizon', 'Inter', sans-serif;
        color: #ffffff;
        font-size: 1.15rem;
        font-weight: 600;
        margin-top: 32px;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 6px;
        letter-spacing: 0.5px;
    }
    p, li {
        color: var(--text-muted);
        font-size: 0.98rem;
    }
    ul {
        padding-left: 24px;
        margin-top: 8px;
    }
    li {
        margin-bottom: 6px;
    }
    code {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
        font-size: 0.88rem;
    }
    .nav-tabs {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
    }
    .nav-tab {
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    .nav-tab.active {
        background: transparent;
        border: 1px solid #ffffff;
        color: #ffffff;
    }
    .nav-tab:not(.active) {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.25);
        color: rgba(255, 255, 255, 0.65);
    }
    .nav-tab:not(.active):hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        border-color: #ffffff;
    }
    .date-badge {
        font-family: 'Inter', sans-serif;
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        font-size: 0.8rem;
        font-weight: 500;
        padding: 4px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .callout {
        background: rgba(255, 255, 255, 0.06);
        border-left: 4px solid #ffffff;
        padding: 16px 20px;
        border-radius: 0 12px 12px 0;
        margin: 24px 0;
    }
    .callout p {
        margin: 0;
        color: #ffffff;
    }
    .footer {
        margin-top: 40px;
        text-align: center;
        font-size: 0.85rem;
        color: var(--text-muted);
        border-top: 1px solid var(--border);
        padding-top: 24px;
    }
    a {
        color: #ffffff;
        text-decoration: underline;
        font-weight: 500;
    }
    a:hover {
        opacity: 0.85;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 640px) {
        body {
            padding: 16px 12px;
        }
        .container {
            padding: 24px 18px;
            border-radius: 16px;
        }
        .brand-header {
            gap: 12px;
            padding-bottom: 18px;
            margin-bottom: 20px;
        }
        .brand-icon {
            width: 44px;
            height: 44px;
        }
        .brand-icon img {
            width: 32px;
            height: 32px;
        }
        .brand-name {
            font-size: 1.2rem;
        }
        .brand-subtitle {
            font-size: 0.8rem;
        }
        h1 {
            font-size: 1.3rem;
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        h2 {
            font-size: 1.05rem;
            margin-top: 24px;
        }
        .nav-tabs {
            gap: 8px;
        }
        .nav-tab {
            padding: 6px 12px;
            font-size: 0.82rem;
        }
        .callout {
            padding: 12px 14px;
            margin: 18px 0;
        }
        p, li {
            font-size: 0.92rem;
        }
    }
</style>
"""

TERMS_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - Sortling</title>
    {COMMON_STYLE}
</head>
<body>
    <div class="container">
        <div class="brand-header">
            <div class="brand-icon">
                <img src="https://raw.githubusercontent.com/sorts-me/Discord/main/Sortling%20Mascot/Icon_Neutral.png" alt="Sortling Mascot">
            </div>
            <div class="brand-title-group">
                <div class="brand-name">Sortling <span class="discord-badge">APP</span></div>
                <div class="brand-subtitle">Mahindra University</div>
            </div>
        </div>

        <div class="nav-tabs">
            <a href="/terms" class="nav-tab active">Terms of Service</a>
            <a href="/privacy" class="nav-tab">Privacy Policy</a>
        </div>

        <h1>Terms of Service <span class="date-badge">Effective: July 2026</span></h1>
        <p>Welcome to <strong>Sortling</strong>. By adding or using the Sortling Discord Application in your server, you agree to comply with and be bound by these Terms of Service.</p>
        
        <h2>1. Agreement to Terms</h2>
        <p>By interacting with Sortling, executing slash commands (such as <code>/sort</code>, <code>/clubs</code>, <code>/events</code>, <code>/about</code>), or completing questionnaires, you acknowledge that you have read, understood, and agreed to these Terms and the Discord Developer Terms of Service.</p>

        <h2>2. Permitted Use</h2>
        <p>Sortling is designed strictly for campus club discovery, organization recommendations, and student engagement. You agree not to:</p>
        <ul>
            <li>Use the bot for any illegal, harmful, or unauthorized activities.</li>
            <li>Attempt to exploit, reverse engineer, or flood the bot's slash command API.</li>
            <li>Use automated scripts or bots to spam interactions or bypass rate limits.</li>
        </ul>

        <h2>3. Accuracy & Verification</h2>
        <p>Sortling provides information derived from official university directories and publicly verifiable student organization resources. While we strive for 100% accuracy, official club registration and membership procedures remain governed by university administration.</p>

        <div class="callout">
            <p><strong>Note:</strong> Recommendation scores generated during <code>/sort</code> quiz sessions are calculated dynamically using multi-vector matching algorithms to guide your discovery experience.</p>
        </div>

        <h2>4. Service Availability & Updates</h2>
        <p>We continuously update Sortling to improve recommendation algorithms and add new campus features. We reserve the right to modify, suspend, or discontinue any part of the service at any time.</p>

        <h2>5. Limitation of Liability</h2>
        <p>Sortling is provided on an "as is" and "as available" basis without warranties of any kind. The developers shall not be liable for any indirect or consequential damages arising out of your use of the application.</p>

        <div class="footer">
            Sortling Discord Application &bull; <a href="/privacy">Privacy Policy</a> &bull; Mahindra University
        </div>
    </div>
</body>
</html>
"""

PRIVACY_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - Sortling</title>
    {COMMON_STYLE}
</head>
<body>
    <div class="container">
        <div class="brand-header">
            <div class="brand-icon">
                <img src="https://raw.githubusercontent.com/sorts-me/Discord/main/Sortling%20Mascot/Icon_Neutral.png" alt="Sortling Mascot">
            </div>
            <div class="brand-title-group">
                <div class="brand-name">Sortling <span class="discord-badge">APP</span></div>
                <div class="brand-subtitle">Mahindra University</div>
            </div>
        </div>

        <div class="nav-tabs">
            <a href="/terms" class="nav-tab">Terms of Service</a>
            <a href="/privacy" class="nav-tab active">Privacy Policy</a>
        </div>

        <h1>Privacy Policy <span class="date-badge">Effective: July 2026</span></h1>
        <p>Your privacy is paramount. This Privacy Policy explains how <strong>Sortling</strong> collects, uses, and safeguards user data in strict compliance with Discord Developer Policy standards.</p>

        <h2>1. Information We Collect</h2>
        <p>Sortling practices strict data minimization. We only collect data necessary to provide personalized club recommendations:</p>
        <ul>
            <li><strong>Discord Identifiers:</strong> Ephemeral Discord User ID and Guild ID to scope quiz sessions and manage server admin permissions.</li>
            <li><strong>Questionnaire Preferences:</strong> Option choices selected during <code>/sort</code> quiz sessions to calculate recommendation scores.</li>
            <li><strong>Feedback & Corrections:</strong> Optional feedback submitted via <code>/feedback</code> or interest refinements (e.g. <em>"Am I wrong?"</em> menu).</li>
        </ul>

        <div class="callout">
            <p><strong>Zero Personal Data Guarantee:</strong> Sortling never collects or stores personal names, phone numbers, email credentials, or private message chat history from your Discord channels.</p>
        </div>

        <h2>2. How We Use Data</h2>
        <p>Collected preference data is used exclusively to:</p>
        <ul>
            <li>Generate multi-vector club recommendation matches and personalized explanations.</li>
            <li>Perform online gradient self-training adjustments to improve club trait mapping over time.</li>
        </ul>

        <h2>3. Data Storage & Security</h2>
        <p>Session data is stored in isolated, secure SQLite database storage hosted on Render cloud infrastructure. We implement appropriate technical safeguards to prevent unauthorized access.</p>

        <h2>4. Data Rights & Deletion</h2>
        <p>Users have full control over their stored data. You can request immediate deletion of your session preferences at any time by executing administrative reset commands or contacting bot administrators.</p>

        <h2>5. Third-Party Sharing</h2>
        <p>We do <strong>NOT</strong> sell, trade, or share user data with third-party advertisers or external services.</p>

        <div class="footer">
            Sortling Discord Application &bull; <a href="/terms">Terms of Service</a> &bull; Mahindra University
        </div>
    </div>
</body>
</html>
"""
