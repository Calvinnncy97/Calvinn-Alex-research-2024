from pprint import pprint
import re
import ujson as json
import pandas as pd
import glob
import os
from tqdm import tqdm
from bs4 import BeautifulSoup
from uuid import uuid4


def search_values_by_key(obj:list|dict, key:str, val:list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if obj.get(key):
                val.append(obj.get(key))
            return search_values_by_key(obj.get(k),key, val )
    elif isinstance(obj, list):
        for i in obj:
            search_values_by_key(i, key, val)

    return val
    


def parse_html():
    all_json_files = glob.glob('/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/response_quora/*.json')
    all_qa_sample = []
    for i in tqdm(all_json_files[5582:]):
        with open(i, "r") as f:
            ann = json.load(f)
        for data in ann:
            if data.get("type") != "html":
                continue
            html_str = data.get("payload")
            soup = BeautifulSoup(html_str, 'html.parser')

            script_tags = soup.find_all('script')
            for tag in script_tags:
                if tag.string is None:
                    continue
                try:
                    # Try to load its content as JSON
                    pattern = r'.push\(\"(\{.*?\})\"\);window'
                    matches = re.findall(pattern, tag.string, re.DOTALL)
                    for match in matches:
                        try:
                            valid = match.replace('\\"', "\"").replace('\\\\', "\\")
                            json_data = json.loads(valid)
                            if json_data.get("data") is None or  json_data is None:
                                continue
                            if json_data["data"].get("node") is None:
                                continue
                            answer_node = json_data["data"].get("node", {}).get("answer")
                            if answer_node is None:
                                continue
                            qid = answer_node.get("question", {}).get("qid")
                            q_slug = answer_node.get("question", {}).get("slug")
                            aid = answer_node.get("aid")
                            upvotes = answer_node.get("numUpvotes")
                            share = answer_node.get("numShares")
                            comment_num = answer_node.get("numDisplayComments")
                            views = num = answer_node.get("numViews")
                            title_text = []
                            answer_text = []
                            q_title_str = answer_node.get("question", {}).get("title")
                            if q_title_str is None:
                                continue
                            title = json.loads(q_title_str)
                            
                            search_values_by_key(title, "text", title_text)
                            answer_json = json.loads(answer_node.get("content"))
                            search_values_by_key(answer_json, "text", answer_text)
                            answer_url = answer_node.get("url")
                            qa_sample = {
                                "question" : " ".join(title_text),
                                "answer" : " ".join(answer_text),
                                "qid" : qid,
                                "aid" : aid,
                                'upvotes' : upvotes,
                                "share" : share,
                                "comments" : comment_num,
                                "views" : views,
                                "answer_url" : answer_url,
                                "question_slug" : q_slug

                            }
                            all_qa_sample.append(qa_sample)
                        except json.JSONDecodeError as e:
                            continue
                except json.JSONDecodeError:
                    # If content is not JSON, just ignore
                    continue
        if len(all_qa_sample) >= 2000:
            df = pd.json_normalize(all_qa_sample)
            df.drop_duplicates(subset="aid", inplace=True)
            print(df)
            all_qa_sample.clear()

            df.to_parquet(f"/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/output/qa/{uuid4().hex}.parquet")

    if len(all_qa_sample) >= 0:
        df = pd.json_normalize(all_qa_sample)
        df.drop_duplicates(subset="aid", inplace=True)
        print(df)
        all_qa_sample.clear()

        df.to_parquet(f"/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/output/qa/{uuid4().hex}.parquet")





def parse_graphql():
    all_json_files = glob.glob('/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/response_quora/*.json')
    all_qa_sample = []
    for i in tqdm(all_json_files):
        with open(i, "r") as f:
            ann = json.load(f)
        line_json = []

        for data in ann:
            if data.get("type") != "graphql":
                continue
            lines = data.get("payload").split("\n")
            for i in lines:
                if not i.startswith("{"):
                    continue
                data = json.loads(i)
                search_values_by_key(data, "answer", line_json)
        for answer_node in line_json:
            qid = answer_node.get("question", {}).get("qid")
            q_slug = answer_node.get("question", {}).get("slug")
            aid = answer_node.get("aid")
            upvotes = answer_node.get("numUpvotes")
            share = answer_node.get("numShares")
            comment_num = answer_node.get("numDisplayComments")
            views = num = answer_node.get("numViews")
            title_text = []
            answer_text = []
            q_title_str = answer_node.get("question", {}).get("title")
            if q_title_str is None:
                continue
            title = json.loads(q_title_str)
            
            search_values_by_key(title, "text", title_text)
            if answer_node.get("content") is None:
                continue 
            answer_json = json.loads(answer_node.get("content"))
            search_values_by_key(answer_json, "text", answer_text)
            answer_url = answer_node.get("url")
            qa_sample = {
                "question" : " ".join(title_text),
                "answer" : " ".join(answer_text),
                "qid" : qid,
                "aid" : aid,
                'upvotes' : upvotes,
                "share" : share,
                "comments" : comment_num,
                "views" : views,
                "answer_url" : answer_url,
                "question_slug" : q_slug

            }
            all_qa_sample.append(qa_sample)
            if len(all_qa_sample) >= 10000:
                df = pd.json_normalize(all_qa_sample)
                df.drop_duplicates(subset="aid", inplace=True)
                print(df)
                all_qa_sample.clear()

                df.to_parquet(f"/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/output/qa/{uuid4().hex}.parquet")
    if len(all_qa_sample) > 0:
        df = pd.json_normalize(all_qa_sample)
        df.drop_duplicates(subset="aid", inplace=True)
        print(df)
        all_qa_sample.clear()

        df.to_parquet(f"/home/alextay96/Desktop/workspace/boson/unified-scraping-framework/output/qa/{uuid4().hex}.parquet")

parse_html()
parse_graphql()

# parse_graphql()