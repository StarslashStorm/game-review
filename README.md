# Game Review

A Django web application for writing and reading game reviews, with authentication powered by Supabase. Not just game any type of topic from IT, and user can up vote or down vote the post and leave comments.

![screenshot mock-up test](./assets/images/mock-up-test.png)

## Table of Contents
1. [Project Overview](#project-overview)
2. [UX Design](#ux-design)
4. [Features](#features)
5. [Technologies Used](#technologies-used)
6. [Testing](#testing)
7. [Tech Stack](#tech-Stack)
9. [Setup](#setup)
10. [Project Structure](#project-structure)
11. [Deployment](#deployment)
12. [Credits](#credits)

## Project Overview

- Create account
- Update profile
- Posting about other topic such as IT topic in general.
- Share detailed reviews of games they've played.
- Browse reviews from other gamers.
- Manage their profile and review history.
- Search for specific games or reviews.
- Up vote or Down vote the review that are left.

[Live site](https://game-review-cqgo.onrender.com)

## UX Design

### Wireframe

This section show the draft and planning for the website.

Wireframe landing page

![Wireframe Landing Page](./assets/images/wireframe-landing-page.png)

Wireframe login page

![Wireframe Login Page](./assets/images/wireframe-login-page.png)

Wireframe edit profile

![Wireframe Edit Profile](./assets/images/wireframe-edit-profile.png)

## Features

### Existing Features

Navbar as can be seen on the left is the logo, in the middle user can search what they looking for, and on the right is the login to redirect user to login/register page.

![navbar screenshot](./assets/images/navbar.png)

Landing page is where the post page where user immidietly see the latest post, at very top there is a search bar for user to input what they like and post including pictures.

![Landing page screenshot](./assets/images/landing-page.png)

This is posting system, allowing user to input title, picture, choose category, and (optional) text

![post system screenshot](./assets/images/post.png)

This is the login page for user to login, and allowing new user to register

![Login/Register page screenshot](./assets/images/login-register-page.png)

This is the profile page, user can see the username and their posts. If user wish to edit their profile just simply click edit profile.

![profile page screenshot](./assets/images/profile-page.png)

This edit profile mode, user can input new username, view email, add information about them self if they want to, and delete their account.

![profile edit page screenshot](./assets/images/edit-profile.png)

#### Editing and deleting posts

The author of a post sees **Edit** and **Delete** buttons on the post page and on their own cards in the feed. Nobody else sees them, and the server also blocks anyone who isn't the author (they get the message "You can only edit/delete your own posts.").

- **Edit** opens the post form already filled in with the current title, content and image. The page says "Edit your post" and the button says "Save changes". The image can be replaced or removed.
- **Delete** opens a confirmation page ("Delete this post? This can't be undone.") with **Cancel** and a red **Yes, delete** button. Nothing is deleted until the user confirms.

#### Editing and deleting comments

Every comment, reply and sub-reply shows small **Edit** and **Delete** links to its author only.

- **Edit** opens a page with the comment already filled in. Empty comments are rejected.
- **Delete** uses the same confirmation page. Deleting a comment also deletes all of its replies.

#### Feedback messages

After an action the user sees a message at the top of the page. It is green for success (for example "Your post was updated."), red for errors and blue for information, and it can be closed with the ✕ button.

#### Logged-out users

- Visitors who aren't logged in see "Log in or create an account to join the conversation" instead of the comment box.
- Trying to create a post while logged out shows "You need to be logged in to create a post" with links to log in or create an account.
- Opening a page that needs an account sends the visitor to the login page with the message "Please log in first to do that."

### Future Feature

1. Change password

## Technologies Used

### Languages

- HTML5
- JavaScript
- Python 3.8

## Tech Stack

- Python 3 + Django 6
- Supabase (Auth + PostgreSQL)

---

## Testing

### Test Results

| Test Case | Description                  | Expected Result                | Actual Result                  | Status |
|----------|------------------------------|--------------------------------|--------------------------------|--------|
| TC01     | Load homepage                | Page loads successfully        | Page loads correctly           | Pass |
| TC02     | Submit review                | Review is saved                | Review saved in database       | Pass |
| TC03     | Invalid input (empty form)   | Show error message             | Error message displayed        | Pass |
| TC04     | Open deployed link           | Website loads                  | Failed in mock-up environment  | Limited |
| TC05     | Upload picture               | Profile updated                | Profile updated                | Pass |
| TC06     | Login (Invalid user)         | User cannot login              | User cannot login              | Pass |
| TC07     | Login (Valid user)           | User login                     | User login                     | Pass |
| TC08     | Register new user            | User recieved an email confirmation then login | User recieved an email confirmation then login | Pass |
| TC09     | Update username              | New username appeared          | New username appeared          | Pass |
| TC09     | User deleting account        | Account deleted                | Account deleted                | Pass |
| TC010    | Upload profile picture       | Profile picture updated        | Profile picture updated        | Pass |
| TC11     | Author opens Edit on own post | Form is filled in with current title, content and image; heading "Edit your post" | | |
| TC12     | Author saves edited post     | Post page shows new content and green "Your post was updated." | | |
| TC13     | Author saves post with empty content | Form shows "Content is required." and post is unchanged | | |
| TC14     | Author removes image while editing and saves | Post no longer shows the image | | |
| TC15     | Another user opens `/edit/<post id>/` directly | Redirected to post with red "You can only edit/delete your own posts." | | |
| TC16     | Author clicks Delete on own post | Confirmation page with Cancel and red "Yes, delete" | | |
| TC17     | Author clicks Cancel on the confirmation page | Back on the post, nothing deleted | | |
| TC18     | Author clicks "Yes, delete"  | Feed shows green "Your post was deleted." and post is gone | | |
| TC19     | Another user opens `/delete/<post id>/` directly | Redirected to post with red error, post not deleted | | |
| TC20     | Edit/Delete buttons on another user's post or comment | Buttons are not shown | | |
| TC21     | Author edits own comment     | Comment form is filled in; after saving, green "Your comment was updated." | | |
| TC22     | Author saves an empty comment | Error "Your comment can't be empty." and comment is unchanged | | |
| TC23     | Author deletes a comment that has replies | Green "Your comment was deleted."; comment and all its replies are gone | | |
| TC24     | Author edits/deletes own reply and sub-reply | Works the same as a top-level comment | | |
| TC25     | Post an empty comment        | Red "Your comment can't be empty." | | |
| TC26     | Logged-out user opens a post | "Log in or create an account to join the conversation" box instead of comment form | | |
| TC27     | Logged-out user tries to create a post in the feed | "You need to be logged in to create a post" with Log in / create account links | | |
| TC28     | Logged-out user opens `/create/` | Login page with blue "Please log in first to do that." | | |
| TC29     | Close a message with the ✕ button | Message disappears | | |
| TC30     | Open `/edit/<random id>/` for a post that doesn't exist | 404 page | | |

- All core features are working as expected.
- The deployed application runs successfully on Render.
- Note: The deployed link may not load in certain environments due to external access restrictions or because the render stop running the link.

### Automated Tests

The automated tests are in `news/tests.py`. They replace Supabase with a small fake in-memory version, and they run on a temporary SQLite database. They never read or change the real Supabase data and don't need a `.env` file.

Run them with:

```bash
python manage.py test news
```

They check that:

- the author can edit and delete their own posts and comments
- other users are blocked from editing or deleting (and see the error message)
- the edit forms are filled in with the existing title, content, image and comment text
- empty posts and empty comments are rejected
- deleting a comment also deletes all of its replies, and deleting a sub-reply keeps its parents
- posts or comments that don't exist give a 404 page
- logged-out users are sent to the login page with "Please log in first to do that.", and the `/api/` URLs return a JSON 401 error instead
- the Edit/Delete buttons only appear for the author, and logged-out users see the login box
- success messages are shown in green and error messages in red

Result: 40 tests, all passing.

### Fixed bugs

- **Saving an edited post crashed.** After saving, the code tried to show `news/list.html`, which doesn't exist. It now goes to the post page and shows "Your post was updated."
- **Any logged-in user could delete any post.** `news_delete` didn't check who wrote the post. Only the author can delete it now, and only after confirming.
- **Removing the image while editing did nothing.** The ✕ button only hid the preview. It now tells the server to remove the image.
- **The create page said "Update a Post".** The heading and button now say "Create a Post" / "Publish Post" when creating and "Edit your post" / "Save changes" when editing.
- **Comment errors showed raw JSON.** For example, posting an empty comment showed `{"error": "Content is required"}`. They now show a normal message on the post page.
- **Creating a post while logged out showed "An error occurred while posting."** The page now explains that you need to log in and links to the login page.
- **JavaScript error on every page.** The user-menu script in `base.html` looked for elements that don't exist. It now checks for them first.

### Unfixed bugs

- There is a bug where render decided to shut down the link that is deployed.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/TimothyYW/game-review.git
cd game-review
```

### 2. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=

# For Django ORM (standard Postgres connection)
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"

ALLOWED_HOSTS=
DEBUG='True'
```

> Get these values from your Supabase project: **Settings → API** and **Settings → Database**.

### 5. Set up the Supabase database

In the Supabase dashboard, go to **SQL Editor** and run the contents of:

```
assets/schema.sql
```

### 6. Run database migrations

```bash
python manage.py migrate
```


### 7. Start the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Project Structure

```
game-review/
├── accounts/       # Auth views, middleware, decorators
├── news/           # Game review CRUD
├── core/           # Settings, URLs, Supabase client
├── templates/      # Base and app-level templates
├── assets/         # schema.sql
└── manage.py
```
## Deployment

This guide walks through deploying this Django application to [Render](https://render.com).

### 1. Project Preparation

Install the required packages:

```bash
pip install gunicorn whitenoise psycopg2-binary python-dotenv
pip freeze > requirements.txt
```

### 2. Make executable a build script 

```bash
chmod a+x build.sh
```

### 3. Render Dashboard Setup

1. Go to [render.com](https://render.com) and create an account
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Select **Environment: Python 3**

Set the following:

| Setting | Value |
|---|---|
| Build Command | `./build.sh` |
| Start Command | `gunicorn core.wsgi:application` |

### 4. Environment Variables

In the Render dashboard, scroll to **Advanced** and add the following environment variables:

```
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=
DATABASE_URL=
ALLOWED_HOSTS=
DEBUG=False
```

Click **Deploy**.

## Credits

- Website for Mock-up test:
  https://techsini.com/multi-mockup/index.php
- Mock-up test solver:
  https://techsini.com/unable-to-generate-mockup-of-your-website-here-is-the-quick-fix/
- Phto use in post is open source.
- The idea pprojcet come and inspired from Code Institute.
