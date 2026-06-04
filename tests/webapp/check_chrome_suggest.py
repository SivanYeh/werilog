import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on("console", lambda msg: print(f"PAGE LOG: {msg.text}"))
        
        async def handle_response(response):
            if "/api/" in response.url:
                print(f"RESPONSE: {response.url} status={response.status}")
                try:
                    body = await response.text()
                    print(f"BODY: {body[:200]}")
                except Exception as e:
                    print(f"Failed to read body: {e}")
                    
        page.on("response", handle_response)
        
        print("Navigating...")
        await page.goto("http://localhost:8001")
        
        await asyncio.sleep(2)
        print("Typing syntax error code...")
        
        await page.evaluate("""
            if (typeof editor !== 'undefined') {
                editor.setValue("module test(\\n");
                // Move cursor to end
                editor.setPosition({lineNumber: 1, column: 13});
                // Trigger suggest
                editor.trigger('keyboard', 'editor.action.triggerSuggest', {});
            }
        """)
        
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
