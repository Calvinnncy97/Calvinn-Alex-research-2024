import asyncio
import os
from pprint import pprint
from playwright.async_api import async_playwright
import ujson as json
from tqdm import tqdm
from loguru import logger
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
import pandas as pd
import uuid
import dataclasses
import ray
import tiktoken
import click

# ray.init(local_mode=False)


@dataclass
class Article:
    url :str
    title : str
    category : str
    published_at : str
    content : str
    root_topic:str
    text_tokens:str
    num_tokens:str

async def worker(url,topic, save_interval:int, output_dir:str):
    output_data = []
    enc = tiktoken.encoding_for_model("gpt-4")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Change headless=False if you want to see the browser
        page = await browser.new_page()
        await page.goto(url)
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href]')).map(link => link.href);
        }''')
        await page.wait_for_timeout(3000)
        for i in tqdm(range(30), desc="page"):
            try:
                elem = page.locator("#ctl00_MainContent_ctl00_ButtonMoreResults", has_text="Load More")
                await elem.click(timeout=3000)
                await page.wait_for_timeout(1000)
                new_links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]')).map(link => link.href);
            }''')
                
                if len(new_links) <= len(links):
                    break
                links = new_links
            except Exception as e1:
                logger.info(f"No more page to load")
                break
                
        links = list(set(links))
        terminal_pages = [x for x in links if re.match(r"https://news\.gallup\.com/.+/\d+/.+\.aspx", x)]
        for url in tqdm(terminal_pages, desc="extract page"):
            try:
                await page.goto(url)
                await page.wait_for_timeout(500)
                title_elem = page.locator('#main > div > article > div > header')
                header_text = await title_elem.all_inner_texts()
                header_text[0] = header_text[0].replace("Share on Facebook\nShare on Twitter\nShare on LinkedIn\nShare via Email\nPrint\n", "")
                metadata = header_text[0].split("\n")
                category = metadata[0]
                date = metadata[1]
                title = metadata[2]

                article_content = page.locator("#main > div > article > div > div.article-content")
                contents = await article_content.inner_text()
                normalized_text = contents.replace("\n\n", "").replace("  ", "").strip()
                text_tokens = enc.encode(normalized_text)
                num_tokens = len(text_tokens)
                output_data.append(Article(
                    url=url,
                    category=category,
                    published_at=date,
                    title=title,
                    content=normalized_text,
                    root_topic=topic,
                    text_tokens=text_tokens,
                    num_tokens=num_tokens
                ))
                if len(output_data) >= save_interval:
                    df = pd.json_normalize([dataclasses.asdict(x) for x in output_data])
                    print(df)
                    df.to_parquet(f"{output_dir}/{uuid.uuid4().hex}.parquet")
                    output_data.clear()
                    logger.success("Saved data")
            except Exception as e2:
                logger.error(f"E2 : {e2}")
                
    if len(output_data) > 0:
        df = pd.DataFrame(output_data)
        print(df)
        df.to_parquet(f"{output_dir}/{uuid.uuid4().hex}.parquet")
        output_data.clear()
        logger.success("Saved data")



async def scheduler(seed_file:str, save_interval:int, output_dir:str):
    pending_task = []
    with open(seed_file, "r") as f:
        seed = json.load(f)
    for topic_item in seed["topics"]:
        url = topic_item['url']
        topic = topic_item['name']
        # worker_wrapper(url, topic, 5)
        pending_task.append(asyncio.create_task(worker(url, topic, save_interval, output_dir)))
    await asyncio.wait(pending_task)

@click.command()
@click.option('--seed_file', default="src/data_engineering/gallup/seed.json", type=str)
@click.option('--save_interval', type=int, default=100)
@click.option('--output_dir', type=str, default="/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/data/gallup/bronze")
def scheduler_runner(seed_file, save_interval, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    asyncio.run(scheduler(seed_file, save_interval, output_dir))
    
    
    
if __name__ == "__main__":
    scheduler_runner()