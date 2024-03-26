import hrequests
from playwright.sync_api import sync_playwright
from tqdm import tqdm
def get_all_hrefs(output_dir):
    with sync_playwright() as p:
        # Launch the browser
        for i in range(1, 100):
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Go to the page
            page.goto(f"https://arxiv-sanity-lite.com/?page_number={i}")
            page.wait_for_timeout(3000)
            # Extract all href attributes from <a> tags
            hrefs = page.eval_on_selector_all("a", "elements => elements.map(element => element.href)")
            valid_aid = [x.split("/")[-1] for x in hrefs if "arxiv.org/abs/" in x]
            for aid in tqdm(valid_aid):
                resp = hrequests.get(f'https://arxiv.org/pdf/{aid}.pdf')
                with open(f"{output_dir}/{aid}.pdf", "wb") as f:
                    f.write(resp.content)
            # Close the browser
          

output_dir = '/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/src/data_engineering/arvix-image/pdf'
hrefs = get_all_hrefs(output_dir)
for href in hrefs:
    print(href)
    