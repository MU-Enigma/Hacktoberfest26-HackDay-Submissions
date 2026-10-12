const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: '/home/sdheeraj/.cache/puppeteer/chrome-headless-shell/linux-155.0.8059.39/chrome-headless-shell-linux64/chrome-headless-shell',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 860, deviceScaleFactor: 2 });

  console.log('Navigating to landing page...');
  await page.goto('http://127.0.0.1:5050', { waitUntil: 'networkidle0' });
  await delay(1000);

  // 1. Log in as Aanya (SE25 · Second Year)
  console.log('Logging in as demo student Aanya...');
  await page.click('[data-demo-email="se25u1001@mahindrauniversity.edu.in"]');
  await page.waitForSelector('#activity-grid .quest-card', { timeout: 10000 });
  await delay(1500);

  console.log('Capturing 01_discover_feed.png...');
  await page.screenshot({ path: path.join(screenshotsDir, '01_discover_feed.png'), fullPage: false });

  // 2. Open activity details
  console.log('Opening activity details...');
  await page.click('#activity-grid .quest-card [data-open-detail]');
  await page.waitForSelector('#view-detail article.detail-card', { timeout: 10000 });
  await delay(1500);

  console.log('Capturing 02_activity_detail.png...');
  await page.screenshot({ path: path.join(screenshotsDir, '02_activity_detail.png'), fullPage: false });

  // 3. Create activity form
  console.log('Navigating to Create Quest...');
  await page.click('[data-nav="create"]');
  await page.waitForSelector('#view-create #create-form', { timeout: 10000 });
  await delay(1000);

  // Fill in sample values for screenshot
  await page.type('#f-title', 'Sunset Polaroid & Chai Walk');
  await page.type('#f-description', 'Bring an appetite for chai and aesthetic photos. We have two extra cameras!');
  await page.select('#f-category', 'Outdoors');
  await page.select('#f-connection', 'either');
  await page.select('#f-invite', 'everyone');
  await page.type('#f-venue', 'Campus Amphitheatre & Lake Path');

  console.log('Capturing 03_create_activity.png...');
  await page.screenshot({ path: path.join(screenshotsDir, '03_create_activity.png'), fullPage: false });

  // 4. Student profile with study year
  console.log('Navigating to Profile...');
  await page.click('[data-nav="profile"]');
  await page.waitForSelector('#view-profile .profile-card', { timeout: 10000 });
  await delay(1500);

  console.log('Capturing 04_student_profile.png...');
  await page.screenshot({ path: path.join(screenshotsDir, '04_student_profile.png'), fullPage: false });

  // 5. Admin Panel
  console.log('Logging in as admin and navigating to /admin...');
  await page.click('#btn-logout').catch(() => {});
  await delay(600);
  await page.click('[data-nav="auth"]');
  await delay(600);
  await page.type('#l-email', 'se24admin@mahindrauniversity.edu.in');
  await page.type('#l-password', 'StrongAdminPassword123');
  await page.click('#login-form button[type="submit"]');
  await delay(1500);

  await page.goto('http://127.0.0.1:5050/admin', { waitUntil: 'networkidle0' });
  await page.waitForSelector('#tbody-activities tr', { timeout: 10000 });
  await delay(1500);

  console.log('Capturing 05_admin_panel.png...');
  await page.screenshot({ path: path.join(screenshotsDir, '05_admin_panel.png'), fullPage: false });

  await browser.close();
  console.log('All 5 screenshots captured successfully!');
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});

