# SideQuest ✿

### Don't just find people. Find your next little adventure.

SideQuest is a whimsical, campus-focused social discovery platform built for Mahindra University students. Discover fun activities, meet people with shared interests, find study buddies, make friends, and maybe even find a date.

Why endlessly swipe through strangers when you could meet someone over board games, coffee, music, or a questionable side project?

## Team

**Team name:** caffeine_sniffers

### Members

- Melvin - sapph-h
- Dheeraj - 17sdheeraj

## Problem

University campuses are full of people with shared interests, but meeting them isn't always easy. Students often stick to their existing friend groups, making it difficult to find new friends, activity partners, or romantic connections.

Existing dating apps focus heavily on individual profiles and swiping, while event platforms focus on activities without necessarily helping people connect.

**The problem isn't a lack of people. It's a lack of opportunities to meet them.**

## Solution

SideQuest makes activities the starting point for social discovery.

Instead of endlessly browsing profiles, students discover activities they'd genuinely enjoy and meet people through shared experiences.

From board-game nights and indie music exchanges to study sessions and photography walks, SideQuest makes it easier to take the first step.

### ✨ Features

- **Activity-first discovery:** Explore campus activities based on interests, categories, and connection preferences.
- **Create your own quests:** Organize activities, set participant limits, choose a venue, and invite others to join.
- **Friends or dates:** Activities can be intended for friendship, dating, or meeting people generally.
- **Interest-based recommendations:** Discover activities that match your interests, with explanations for why they're recommended.
- **Student profiles:** Showcase your interests, bio, profile picture, and university year.
- **Campus connections:** Meet people through shared activities rather than relying exclusively on profile-based matching.
- **Whimsical experience:** A colourful scrapbook-inspired interface with playful dialogue, pastel cards, doodles, and delightful interactions.

Additional features, including account management and gender-specific activity eligibility, depend on the functionality implemented in the submitted version.

## Technologies Used

- Python
- Flask
- SQLite
- HTML, CSS, and JavaScript
- Docker (if included in the submitted version)

## How to Run

### Prerequisites

- Python 3.11 or a compatible version supported by the project
- Git

### 1. Clone the repository

```bash
git clone <YOUR-FORK-URL>
cd <YOUR-REPOSITORY>
```

Navigate to the SideQuest project directory inside `submissions/` if applicable.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the application

Create a `.env` file if required by the implementation. Use the provided `.env.example` as a reference.

Do not commit passwords, secret keys, or other credentials.

### 5. Start the application

Use the startup command documented by the project. For a standard Flask application, this may be:

```bash
flask --app app run --debug
```

Open the local URL displayed in the terminal, typically `http://127.0.0.1:5000`.

If the project includes Docker support, see the Docker instructions in the repository.

## Demo

**Screenshots**

Add screenshots of the following:

- Discover page
- Activity details and joining
- Create-a-quest form
- Student profile
- Interest-based recommendations

**Screen recording:** ADD DEMO VIDEO LINK

**Live deployment:** ADD LINK IF AVAILABLE

## Notes

SideQuest was developed as part of **Hack Day | Hacktoberfest 2026**, hosted by Enigma at Mahindra University.

The project is a hackathon prototype. Demo accounts and sample activities may be used to demonstrate the experience.

Features and security controls should be evaluated against the actual submitted implementation. Real-world deployment would require additional work on authentication, privacy, moderation, abuse prevention, and student eligibility verification.

### Future Ideas

- Smarter activity recommendations
- Group conversations for joined activities
- Notifications for upcoming activities
- Calendar integration
- Better activity matching based on availability
- Expanded reporting and moderation tools

---

**SideQuest — find your people, one little adventure at a time.** ✿

---

Try it out now at: http://mu-sidequest.sdheeraj.is-cool.dev/
