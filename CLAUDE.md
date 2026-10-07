# Project notes

Remotion project (`npm run dev` for the studio, `npm run lint` for checks).

## Banners: Google Drive only, never in git

Banner material (images, PSD/AI sources, fonts) is client data. It lives on
Google Drive and must never be committed or pushed.

- **Source:** Drive folder `Per Claude / 07. BANNER ONLINE`
  (id `1Ne9A-XSqwPLcMcOx0syRtSweQw63XGlU`), with subfolders `07.1. BANNERS`,
  `07.2. BANNERS CHECKOUT`, `07.3. BANNERS NEWSLETTER`.
- **Local copy:** `public/private/` — git-ignored, and `.githooks/pre-commit`
  refuses any commit that stages it anyway (`npm install` enables the hook via
  `prepare`; or run `git config core.hooksPath .githooks`).
- **Fetching:** the folder is over 1 GB, so download only the files a task
  needs, never mirror it. With the Google Drive connector: find the file with
  `search_files` (`parentId = '<folder id>'`), download it with
  `download_file_content`, then decode the saved result:

  ```console
  python3 scripts/drive/save_from_mcp.py <saved-download.json> [subdir]
  ```

- **In code:** reference files as `staticFile("private/<subdir>/<name>")`.
  A fresh clone does not have them, so fetch them before rendering.
- Do not copy client names, file names or Drive contents into commit messages,
  code comments or other tracked files.
