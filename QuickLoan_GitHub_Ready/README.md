# QuickLoan Demo

A mobile-friendly **loan application demonstration** built with Flask and SQLite. It is a prototype for learning and portfolio use, not a real lending service.

## Features
- Loan application form and reference number
- Application status lookup
- Admin login and dashboard
- Admin can update application statuses
- Temporary admin access links can be created, expire, and be revoked
- Responsive layout for mobile and desktop

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (optional but recommended).
4. Run `pip install -r requirements.txt`.
5. Set environment variables for `APP_SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`.
6. Run `python app.py`.
7. Visit `http://127.0.0.1:5000`.

Example environment values are for local testing only. Do not use default credentials on a public website.

## Deploying on Render
1. Upload the **contents** of this folder to a GitHub repository (do not upload only the ZIP file).
2. In Render, create a new Web Service and connect the repository, or use the included `render.yaml`.
3. Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the Render environment settings.
4. Ensure a persistent disk is configured if you need the SQLite database to survive redeploys. For production, use a managed database instead.
5. Set a strong secret key. Never commit secrets or real user information to GitHub.

## Important safety notes
- Use your own brand and clearly identify this as a demo.
- Do not imitate a bank, mobile-money provider, or other organization without written authorization.
- Never request or store mobile-money PINs, passwords, or one-time verification codes.
- This demo does not approve or issue real loans.
- Before real-world use, add CSRF protection, rate limiting, stronger authentication, secure database hosting, privacy notices, and legal/compliance review.
