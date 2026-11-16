// Prints the HTML guides written by build_guides.py to A4 PDF.
// Usage: node print_guides.cjs jobs.json   (jobs: [{html, pdf}, ...])
const fs = require("fs");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const job of jobs) {
    await page.goto(pathToFileURL(job.html).href, { waitUntil: "load" });
    await page.pdf({
      path: job.pdf,
      format: "A4",
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: "<span></span>",
      footerTemplate:
        '<div style="width:100%;font:8px Helvetica,Arial,sans-serif;color:#8a8170;text-align:center">' +
        '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
      margin: { top: "14mm", bottom: "16mm", left: "14mm", right: "14mm" },
    });
  }
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
