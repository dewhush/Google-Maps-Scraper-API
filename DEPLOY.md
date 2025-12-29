# Deploying LeadMaps to Render

You are all set to deploy! I've configured your project with the necessary files (`render.yaml`, `render-build.sh`).

## Step 1: Push Changes to GitHub

Since I encountered a git lock error, please run these commands in your terminal to commit and push proper code:

```bash
# 1. Clear any stale git locks (if you see an error)
rm -f .git/index.lock

# 2. Stage and commit all changes
git add .
git commit -m "feat: configure for Render deployment"

# 3. Push to GitHub
git push origin main
```

## Step 2: Create Account / Login to Render

1. Go to [dashboard.render.com](https://dashboard.render.com/).
2. Login with your GitHub account.

## Step 3: Create Blueprint Instance

1. Click **New +** button in the top right.
2. Select **Blueprint**.
3. Connect your `Lead Maps` repository.
4. Render will automatically read the `render.yaml` file and propose 2 services:
   - **leadmaps-backend**: The Python FastAPI server
   - **leadmaps-frontend**: The React static site
5. Click **Apply**.

## Step 4: Configure Environment Variables

Render will ask for values for the environment variables defined in `render.yaml`. Use these values:

| Variable | Value |
|----------|-------|
| `RESEND_API_KEY` | `re_...` (Your actual Resend API Key) |
| `MAIL_FROM` | `team@leadmaps.web.id` |
| `SECRET_KEY` | (Click "Generate" or enter a random string) |

## Step 5: Finalize

1. Render will start building both services.
2. The **backend** build might take a few minutes as it installs Chrome.
3. Once deployed, Render will give you a URL for the frontend (e.g., `https://leadmaps-frontend.onrender.com`).

**Note:** The app is configured to handle the backend connection automatically.
