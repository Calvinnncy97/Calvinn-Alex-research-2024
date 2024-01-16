import asyncio
import glob

from playwright.async_api import async_playwright, Request, Page, Playwright, Route, BrowserContext
from tqdm import tqdm
import pandas as pd
from uuid import uuid4
from loguru import logger
import random
import os
import ujson as json


class SeedDataRepo:
    def __init__(self) -> None:
        self.seed_question = []
        self.seed_topic = []
        self.seed_user = []
        self.seed_collection = []
        self.seed_rountable = []
        self.scroll_down = 5
        self.output_dir = "/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/response_quora"
        self.output_dir_2 = "/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/users_quora"
        self.output_dir_3 = "/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/seen_quora"
        self.current_url = 'https://www.quora.com/profile/Justin-Franco-1'
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.output_dir_2, exist_ok=True)
        os.makedirs(self.output_dir_3, exist_ok=True)

        self.payload = []

    async def extract_data(self, urls:list):
        urls = [x for x in urls if "waiting" not in x]
        question_url = set([x.replace("?write", "").split("/answer/")[0] for x in urls if "/question/" in x])
        topic_url = set([x for x in urls if "/topic/" in x])
        user_url = set([x.replace("/followers", '').replace("/following", "").replace("/pins", "").replace("questions", "").replace("collections", "").replace("columns", "") for x in urls if "/people/" in x])
        collection_url = set([x for x in urls if "/collection/" in x])
        roundtable_url = set([x + "/latest-all" for x in urls if "/roundtable/" in x])
        self.seed_question.extend(list(question_url))
        self.seed_topic.extend(list(topic_url))
        self.seed_user.extend(list(user_url))
        self.seed_collection.extend(list(collection_url))
        self.seed_rountable.extend(list(roundtable_url))
       

    

        
    async def persist_api(self, qid) :
        if len(self.payload) == 0:
            return
        with open(f"{self.output_dir}/{qid}.json", "w") as f:
            json.dump(self.payload, f, ensure_ascii=False, indent=4, escape_forward_slashes=False)
        with open(f"{self.output_dir_2}/{qid}.json", "w") as f:
            json.dump(list(set(self.seed_user + self.seed_topic)), f, ensure_ascii=False, indent=4, escape_forward_slashes=False)
        logger.success(f"Successfully saved {len(self.payload)} data  from question : {qid}")
        self.payload.clear()
       


    async def shuffle_url(self):
        random.shuffle(self.seed_collection)
        random.shuffle(self.seed_topic)
        random.shuffle(self.seed_question)
        random.shuffle(self.seed_rountable)
        
    async def handle_response(self, req:Route):
        
        if "q=CommentableCommentAreaLoaderInnerQuery" in req.request.url \
        or 'q=QuestionPagedListPaginationQuery' in req.request.url \
        or self.current_url in req.request.url \
        and "ajax" not in req.request.url \
        and "POST?q=UserProfileSpacesSection_Paging_Query" not in req.request.url:
            if "CommentableCommentAreaLoaderInnerQuery" in req.request.url:
                resp = await req.fetch()
                resp_json = await resp.json()
                self.payload.append(
                    {
                        "url" : req.request.url,
                        "payload" : resp_json,
                        "type" : "json"
                    }
                )
            else:
                try:
                    resp = await req.fetch()
                    resp_json = await resp.text()
                    
                    self.payload.append(
                        {
                            "url" : req.request.url,
                            "payload" : resp_json,
                            "type" : "graphql" if 'QuestionPagedListPaginationQuery' in req.request.url else "html"

                        }
                )
                except Exception as e5:
                    print(e5)
            logger.success(f"Intercepted : {req.request.url}")
            await req.fulfill(response=resp)
        else:
            await req.continue_()




async def run(context:BrowserContext, profile_answer_url:list, scroll_down_num:int, max_comment_expanded: int):

   

    for q in profile_answer_url[:10]:
        data_repo = SeedDataRepo()
        page = await context.new_page()
        page.set_default_timeout(30000)
        await page.route("**/*", data_repo.handle_response)

        try:
            data_repo.current_url = q

            await page.goto(q)

            for _ in tqdm(range(scroll_down_num), desc="scrolling"):
                await page.keyboard.press("End")
                await page.wait_for_timeout(500)


            urls = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
            urls = list(set([x.split("/answer/")[0] for x in urls if "/profile/" not in x 
                            and "/topic/" not in x 
                            and "/about/" not in x 
                            and x!= "https://www.quora.com/" 
                            and "/answer/" in x]))
            for u in urls[:30]:
                try:
                    question_name = u.split("/")[-1]
                    seen_question = [x.replace(".json", "") for x in os.listdir(data_repo.output_dir)]
                    if question_name in seen_question:
                        logger.info("Skipping seen question")
                        continue
                    data_repo.current_url = u
                    await page.goto(u)
                    for i in range(10):
                        await page.keyboard.press("End")
                        await page.wait_for_timeout(500)
                    
                    buttons = page.locator('[role="button"]')
                    comment_expanded = 0
                    for i in range(await buttons.count()):
                        button = buttons.nth(i)
                        aria_label = await button.get_attribute('aria-label')
                        if aria_label is None or "comment" not in aria_label:
                            continue
                        await button.click()
                        comment_expanded += 1
                        if comment_expanded >= max_comment_expanded:
                            break
                    await data_repo.persist_api(question_name)
                except Exception as e3:
                    logger.warning(f"E3 : {e3}")

        except Exception as e2:
            logger.warning(f"E2 : {e2}")
       
        finally:
            await page.close()
    

async def main(scroll_down_num, max_comment_expanded):
        dir = "/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/quora_seeds"
        all_seeds = []
        for i in glob.glob(f'{dir}/*.csv'):
            df = pd.read_csv(i)
            all_seeds.append(df)
        complete_seed_df = pd.concat(all_seeds)
        print(complete_seed_df)
        complete_seed_df.drop_duplicates(subset="url", inplace=True)
        profile_df =  complete_seed_df[complete_seed_df["url"].str.contains("/profile/")]
        print(profile_df)
        profile_answer_url = profile_df["url"].tolist()
        profile_df["url"] = profile_df["url"].apply(lambda x : f"{x}/answers")

        for _ in range(1000):

            try:
                all_parallel_task = []
                async with async_playwright() as playwright:
                    context = await playwright.chromium.launch_persistent_context(
                        "/home/alextay96/.config/google-chrome/Default",
                        
                        headless=False)
                    for i in range(10):
                        profile_df = profile_df.sample(frac=1.0)
                        print(profile_df)
                        profile_answer_url = profile_df["url"].tolist()
                        all_parallel_task.append(
                            asyncio.create_task(
                                run(context, profile_answer_url, scroll_down_num, max_comment_expanded)
                            )
                        )
                    await asyncio.wait(all_parallel_task)
                

                
            except Exception as e0:
                logger.error(f"E0 : {e0}")


if __name__ == "__main__":
    scroll_down_num = 20
    max_comment_expanded = 10
    asyncio.run(main(scroll_down_num, max_comment_expanded))