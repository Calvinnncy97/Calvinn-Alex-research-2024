import asyncio

from playwright.async_api import async_playwright, Request, Page, Playwright, Route, BrowserContext
from tqdm import tqdm
import pandas as pd
from uuid import uuid4
from loguru import logger
import random

class SeedDataRepo:
    def __init__(self) -> None:
        self.seed_question = []
        self.seed_topic = []
        self.seed_user = []
        self.seed_collection = []
        self.seed_rountable = []
        self.scroll_down_fast = 30
        self.scroll_down = 50
        self.output_dir = "/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/quora_seeds"

    async def extract_data(self, urls:list):
        urls = [x for x in urls]
        question_url = set([x.replace("?write", "") for x in urls if "/answer/" in x])
        topic_url = set([x for x in urls if "/topic/" in x])
        user_url = set([x for x in urls if "/profile/" in x])
        self.seed_question.extend(list(question_url))
        self.seed_topic.extend(list(topic_url))
        self.seed_user.extend(list(user_url))
        
       

    
    async def persist_seeds(self):
        df = pd.DataFrame(
            {
                "url" : self.seed_question + self.seed_topic + self.seed_user + self.seed_collection + self.seed_rountable
            }
        )
        df.to_csv(f"{self.output_dir}/seed_url_{uuid4().hex}.csv")
        logger.success("Saved seeds to file")
        


    async def shuffle_url(self):
        random.shuffle(self.seed_collection)
        random.shuffle(self.seed_topic)
        random.shuffle(self.seed_question)
        random.shuffle(self.seed_rountable)

    
async def explore_url(tasks:list, page:Page, scroll_down_num:int, data_repo:SeedDataRepo, save_file:bool = True, check_pop_up:bool = True):
    page.set_default_timeout(3000)
    for collection in tasks:
        try:
            await page.goto(collection)
            await page.wait_for_timeout(1000)
            try:
                if check_pop_up:
                    cancel_button  = page.locator('button[aria-label="关闭"]')

                    if cancel_button is None:
                        continue
                    await cancel_button.click()
            except Exception as e1:
                    logger.warning(f"E1 cancel button : {e1}")    
            for _ in tqdm(range(scroll_down_num), desc="scrolling"):
                
                await page.keyboard.press("End")
                await page.wait_for_timeout(300)
            
                if scroll_down_num % 30 == 0:
                    urls = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
                    urls = [x for x in urls if collection != x]
                    await data_repo.extract_data(urls)
            
            urls = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
            await data_repo.extract_data(urls)
            if save_file:
                await data_repo.persist_seeds()
        except Exception as e2:
            logger.warning(f"E2 : {e2}")

async def run(context:BrowserContext):
    async def handle_request(request:Route):
 
        print(request.request.url)
        await request.continue_()

    # Navigate to Zhihu
   
    data_repo = SeedDataRepo()
    query = ["https://www.quora.com/"]
    for i in range(100):
        page = await context.new_page()

        for q in query:
            await page.goto(q)
            scroll_down_num = 100
            for _ in tqdm(range(scroll_down_num), desc="scrolling"):
                await page.keyboard.press("End")
                await page.wait_for_timeout(500)

        
            urls = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
            await data_repo.extract_data(urls)
        await page.close()
        await data_repo.persist_seeds()

        
       

    

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, channel="msedge")

        context = await browser.new_context()
        page:Page = await context.new_page()
        await page.goto("https://www.quora.com")
        await page.wait_for_timeout(60000)  
        for _ in range(1000):
            try:

                    await run(context)
                    await context.close()
                    await browser.close()
            except Exception as e0:
                logger.error(f"E0 : {e0}")


if __name__ == "__main__":
    asyncio.run(main())