const puppeteer = require('puppeteer');

(async () => {
    try {
        console.log("Launching browser...");
        const browser = await puppeteer.launch({headless: "new"});
        const page = await browser.newPage();
        
        page.on('console', msg => console.log('PAGE LOG:', msg.text()));
        page.on('pageerror', err => console.log('PAGE ERROR:', err.toString()));
        page.on('requestfailed', request =>
          console.log('REQUEST FAILED:', request.url(), request.failure().errorText)
        );
        page.on('response', async response => {
            if (response.url().includes('/api/parse') || response.url().includes('/api/suggest')) {
                console.log(`RESPONSE: ${response.url()} status=${response.status()}`);
                try {
                    const text = await response.text();
                    console.log(`BODY:`, text.substring(0, 100));
                } catch(e) {
                    console.log("Could not read body", e);
                }
            }
        });
        
        console.log("Navigating to http://localhost:8001...");
        await page.goto('http://localhost:8001', {waitUntil: 'networkidle2'});
        
        console.log("Waiting for editor...");
        await page.waitForTimeout(2000);
        
        console.log("Typing code...");
        await page.evaluate(() => {
            if (typeof editor !== 'undefined') {
                editor.setValue("module test();\n    wire a;\n    assign a = b;\nendmodule\n");
            } else {
                console.log("Editor not found");
            }
        });
        
        console.log("Waiting for API calls to complete...");
        await page.waitForTimeout(2000);
        
        console.log("Testing syntax error...");
        await page.evaluate(() => {
            if (typeof editor !== 'undefined') {
                editor.setValue("module test(\n");
            }
        });
        
        await page.waitForTimeout(3000);
        await browser.close();
        console.log("Done");
    } catch(e) {
        console.error("Script error", e);
    }
})();
