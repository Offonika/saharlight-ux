import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def run() -> None:
    html_path = Path(__file__).with_name("e2e_reminder_flow.html").as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(html_path)
        # add reminder
        await page.fill("input.new-todo", "Check insulin levels")
        await page.press("input.new-todo", "Enter")
        # edit reminder
        await page.dblclick("css=.todo-list li .view label")
        await page.fill("css=.todo-list li.editing .edit", "Check glucose after dinner")
        await page.press("css=.todo-list li.editing .edit", "Enter")
        # delete reminder
        await page.hover("css=.todo-list li")
        await page.click("css=.todo-list li .destroy")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
