# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/a6cc1696-4643-4e14-b587-2421843125e1

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/a6cc1696-4643-4e14-b587-2421843125e1) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & pnpm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
pnpm install

# Step 4: Start the development server with auto-reloading and an instant preview.
pnpm run dev
```

## Testing

Run the Vitest suite to verify the UI behavior:

```sh
pnpm test
```

You can also invoke the runner directly:

```sh
pnpm vitest run --config ../../../vitest.config.ts
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## Hardware acceleration

The web client prefers hardware-accelerated rendering via WebGL. If the browser
falls back to software rendering, the application will show a warning and some
graphics features may be disabled. In trusted environments that still require
software rendering, start the browser with
`--enable-unsafe-swiftshader` to allow SwiftShader.

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/a6cc1696-4643-4e14-b587-2421843125e1) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/tips-tricks/custom-domain#step-by-step-guide)

## Testing

> **Warning:** `pytest` is intended for backend tests and should be run from the project root, for example:

```bash
pytest tests/
```

Running `pytest` inside this front-end directory is not supported.
