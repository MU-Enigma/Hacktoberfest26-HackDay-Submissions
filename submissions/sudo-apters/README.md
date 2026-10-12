**Project Name: JUNOMate**\
\
**Team**\
Team Name: Sudo Apters\
\
**Members**\
Archisha Gupta - @Archisha-inCode\
Riddhima Teli - @Ridim334\
\
**Problem**\
Classes! 75% Attendance!  EVERYBODY'S NIGHTMARE!\
We spend a lot of our time just thinking  out about hitting that 75 and then we just put in so much effort calculating what all classes to attend and what all can be skipped.
When I ask my seniors what is one of their regrets from their first year, you wouldn't believe what they said. Their biggest regret turned out to be the fact that
they attended more classes than necessary or that they did not maintain their attendance record properly causing them to have major inconviniences with the ERP office and their professors that too right before exams.\
\
This is also a problem I have personally faced. I attend classes to hit that 75 but then I see that my attendance increases by a really small margin BUT when I miss a class, I am down by a large margin.\
\
So, what if, this whole issue could be avoided? The whole process optimized, such that, you no longer have to worry about calculating attendance and not having to break your head over what all classes should be attended and what all classes could be skipped?\
\ 
**Solution**\
All of this process can be made simpe.\
Instead of sitting down, over calculating, what if all you had to do was, install a** chrome extension**?
\
This is where our solution comes in. We have built a chrome extension called **JUNOMate**.
\
**How does our solution work?**\
1) The chrome extension (Also works on Brave Browser) can access the data (Your attendance record and time table) in your JUNO from your browser (You have to log into your JUNO account on the site 
https://muerp.mahindrauniversity.edu.in/).\ 
2) Now it extracts the data required from the site.\
3) It processes the data it has extracted in order to make suggestions on what all classes you need to attend to fulfill the individual and overall attendance requirement, and what all classes can be skipped to be saving you time.
\
**Additional Features**\

User can select what all classes they cannot attend in the future, which the model will take into consideration and come up with a plan for the user accordingly.\

**Advantages our extension has over the user manually estimating their attendance increase decrease**\
Our extension is the most accurate thing so far. You won't be caught by surprise by the way your attendance is affected by the amount of classes that you've attended for the day. This helps you plan your schedule, give time to personal projects, developing skills etc. in a much more efficient manner instead of just playing a game of guess :) \
\
**Technologies Used**\
| Layer | Technology | Purpose |
|-------|------------|---------|
| Browser extension | Chrome Extension, Manifest V3 | Runs inside Chrome on the Juno ERP site |
| Data collection | Content script (JavaScript, DOM API) | Reads the attendance table and today's timetable from the page you're already logged into |
| Storage | `chrome.storage.local` | Saves scraped data on your own machine |
| Messaging | `chrome.runtime` messaging | The popup's Rescan button asks the content script to scan again |
| Extension UI | HTML, CSS, vanilla JavaScript | Popup showing overall %, per-subject %, skip/attend advice and today's plan |
| Web app | React and Vite | Dashboard with subject cards, targets, what-if inputs and today's plan |
| Logic | Plain JavaScript module (`attendance.js`) | Attendance math, shared by the popup and the app |
| Tooling | Node.js and npm | Runs the React dev server | 
\
**How to run**\	
1. Download the zip file.
2. Extract the file.
3. Open Chrome and go to `chrome://extensions`.
4. Turn on **Developer mode** in the top-right corner.
5. Click **Load unpacked** and select the folder containing the extension files.
6. Click the puzzle-piece icon in Chrome and pin the extension.
7. Log in to Juno and open the attendance page (`studentCourses.htm`).
8. Press **F5** to refresh the page.
9. Open the extension popup and click **Rescan**.
10. Check that the attendance total matches Juno's.
11. Check the extension popup for guidance on which classes you can skip, or use the dashboard to explore attendance scenarios and see how many classes you need to attend.
\
**Notes**
Future Features: If a leave is being planned in the future, the software considers that too and makes suggestions accordingly.\
\
Troubleshooting/more plans for the future: Get this extension to function on the very JUNO app itself and be more user friendly. It should be able to analyse the pending assignments, new notifications about events and extra classes.\

## Troubleshooting the JunoMate Extension

1. **Extension not appearing in Chrome:** Go to `chrome://extensions` and check whether JunoMate is enabled.
2. **Extension not installing:** Make sure you selected the correct folder containing `manifest.json`, `content.js`, `popup.html`, and `popup.js`.
3. **Extension showing an error:** Open `chrome://extensions`, find JunoMate, and click **Errors** to see what went wrong.
4. **Rescan not working:** Refresh the Juno page using **F5**, reopen the extension, and click **Rescan** again.
5. **Attendance data not showing:** Make sure you are logged in to Juno and have opened the correct attendance page (`studentCourses.htm`).
6. **Attendance percentage is incorrect:** Compare the extension's total with Juno's attendance summary. Refresh the page and rescan to capture the latest data.
7. **Some subjects are missing:** Check whether all subjects appear on Juno's attendance page, then refresh the page and rescan.
8. **Timetable not showing:** Open Juno's home page (`home.htm`), wait 2 seconds, and click **Rescan**.
9. **Extension showing old data:** Return to the relevant Juno page, refresh it, and click **Rescan** again.
10. **Extension popup is blank or stuck:** Close the popup, refresh the Juno page, and reopen the extension.
11. **Extension stopped working after a Juno update:** Reload JunoMate from `chrome://extensions`, refresh Juno, and try scanning again.
12. **Extension cannot access Juno:** Make sure you are logged in and using Juno in the same Chrome profile where the extension is installed.
13. **Open in app is not working:** Check whether the extension has captured attendance data and try rescanning the attendance page. (This button may also depend on the dashboard being available.)
14. **Still not working:** Open `chrome://extensions`, click **Errors** under JunoMate, and note the error message so it can be investigated.
