# Cook Profile Dashboard

A React and Vite dashboard for loading and comparing cook profiles from CSV and Excel files. Files are processed in the browser and are not uploaded to a server by this application.

## Included

- Multi-file CSV, XLS, and XLSX upload
- Multi-sheet Excel import
- Automatic time and temperature column detection
- Common elapsed-time chart
- Profile visibility and deletion controls
- Celsius and Fahrenheit display
- GitHub Pages deployment workflow

## Data format

Each worksheet or CSV should contain:

- One column whose heading contains `time`, `date`, `hour`, or `elapsed`
- One numeric column whose heading contains `temp`, `probe`, `meat`, `point`, or `flat`

The first matching temperature column is used. The app does not perform tenderness analysis.

## Run locally

1. Install Node.js 22 or a compatible current LTS release.
2. Open a terminal in this folder.
3. Run:

```bash
npm install
npm run dev
```

4. Open the local address shown by Vite.

## Test the production build

```bash
npm run build
npm run preview
```

The production files are written to `dist`.

## Create the GitHub repository

1. Create a new empty repository in GitHub.
2. Extract this package and open the extracted folder in GitHub Desktop.
3. Choose **File > Add local repository**. If prompted, create a repository in this folder.
4. Commit all files with the message `Initial cook profile dashboard`.
5. Choose **Publish repository** and select the required visibility and organization.
6. Keep the default branch named `main`.

Command-line alternative:

```bash
git init
git add .
git commit -m "Initial cook profile dashboard"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

## Deploy with GitHub Pages

1. In the GitHub repository, open **Settings > Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Open **Actions** and select `Deploy dashboard to GitHub Pages`.
4. Run the workflow manually, or push a commit to `main`.
5. The deployed URL appears in the completed deployment job and in **Settings > Pages**.

The workflow automatically sets the Vite base path from the repository name, builds the app, uploads `dist`, and deploys it to GitHub Pages.

## Updating the deployed app

Commit and push changes to `main`. The included workflow rebuilds and redeploys the dashboard.

## Branching recommendation

Keep `main` as the deployed version. Create a development branch for changes:

```bash
git switch -c develop
git push -u origin develop
```

Merge reviewed changes into `main` when ready to deploy.

## Important limitations

- Automatic column selection currently uses the first matching temperature column.
- Workbook formatting and formulas are not retained.
- Large files may affect browser performance.
- Do not commit cook data, confidential information, credentials, or API keys to the repository.
