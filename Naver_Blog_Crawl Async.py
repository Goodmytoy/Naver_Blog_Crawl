import os
import sys
import urllib
import urllib3
import requests
import json
import xmltodict
import re
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
import numpy as np
from typing import Union
from tqdm import tqdm
from lxml import etree
from copy import deepcopy
import pickle
import asyncio
import functools



# Hide Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime
import os
import inspect
import functools

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def requests_retry_session(
    retries=5,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_execution_time(func):
    """
        시간을 측정하는 Decorator 함수

        Args: 
            func: 대상 Function

        Returns:
            wrapper function
            
        Exception: 
    """
    @ functools.wraps(func)
    def wrapper_check_execution_time(*args, **kwargs):
        start_time = datetime.now()  

        result = func(*args, **kwargs)
        
        end_time = datetime.now()
        print(f"{func.__name__} execution time: {end_time - start_time}")
        return result
    return wrapper_check_execution_time

class NaverBlogCrawl:
    
    client_id = "VyJ4vDh18O7CVkYDCROr"
    client_secret = "pOn2vw75sv"
    TIME_VERBOSE = True
    def __init__(self):
        pass


    # @check_execution_time
    def search_blogs_by_API(self, keyword:str, display:int) -> dict:
        blog_infos = defaultdict(list)
        self.keyword = keyword
        # API를 통한 검색
        encText = urllib.parse.quote(self.keyword)
        url = f"https://openapi.naver.com/v1/search/blog.xml?query={encText}&display={display}"

        headers = {"X-Naver-Client-Id" : self.client_id,
                   "X-Naver-Client-Secret" : self.client_secret}
        rq = requests_retry_session().get(url, headers=headers, verify=False)
        html = rq.text
        html_dict = xmltodict.parse(html)
        self.html_dict = html_dict

        if html_dict["rss"]["channel"]["total"] == "0":
            blog_infos = None
        else:
            blog_infos = html_dict["rss"]["channel"]["item"]

        
        return blog_infos


    # @check_execution_time
    def create_blog_request_params(self, blog_info:dict) -> str:
        # 실제 Url 찾기
        blog_link = blog_info["link"]
        blogger_link = blog_info["bloggerlink"]

        logNo = re.search(r"logNo=([\d]+)", blog_link).group(1)
        bloggerId = blogger_link.split("/")[-1]

        # blog_url = f"https://blog.naver.com/PostView.naver?blogId={bloggerId}&logNo={logNo}&from=search&redirect=Log&widgetTypeCall=true&directAccess=false"
        blog_request_params = {"blogId" : bloggerId,
                               "logNo" : logNo,
                               "from" : "search",
                               "redirect" : "Log",
                               "widgetTypeCall" : "true",
                               "directAccess" :"false"}
        return blog_request_params


    # @check_execution_time
    def save_images(self, img_urls:str, img_names:str, img_dir:str = "./image"):

        if img_dir is None:
            img_dir = f"./image/{self.keyword}"
        
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        self.error_list = []
        for img_url, img_name in zip(img_urls, img_names):
            # image 저장        
            try:
                img_rq = requests.get(img_url, verify = False)
                with open(f"{img_dir}/{img_name}", "wb") as f:
                    f.write(img_rq.content)
            except: 
                self.error_list.append(img_name)
                print(f"img_name : {img_name}, img_url : {img_url}")
    

    def collect_tags(self, blog_soup:BeautifulSoup):
        blog_soup.find("a", attrs={"class":"item pcol2 itemTagfont _setTop"})
    
    # @check_execution_time
    async def parse_smarteditor_one(self, blog_body, keyword = "temp", blog_info:dict = None) -> dict:
        # https://blog.naver.com/PostView.naver?blogId=dreaminguth&logNo=222637214855&redirect=Dlog&widgetTypeCall=true&directAccess=false
        
        for br in blog_body.findall("br"):
            br.replace_with("\n")

        # 본문 내에 Image와 Text가 있는 부분만 추출
        blog_img_txt = blog_body.xpath(".//div[re:match(@class, 'se-(module|section)-(text|image)')]", 
                                       namespaces={"re": "http://exslt.org/regular-expressions"})
        
        blog_contents_dict = defaultdict(list)        

        # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
        raw_blog_contents = []
        img_urls = []
        img_names = []
        img_num = 0

        for x in blog_img_txt:
            if re.search(r"se-(module|section)-image", x.attrib["class"]) is not None:
                
                try: 
                    if "data-lazy-src" in x.find(".//img").attrib.keys():
                        img_url = x.find(".//img").attrib["data-lazy-src"]
                    else:
                        img_url = x.find(".//img").attrib["src"]
                except:
                    continue
                
                if img_url in img_urls:
                    continue
                else:
                    img_urls.append(img_url)
                
                img_num += 1
                img_name = f"[{keyword}_{blog_info['bloggername']}_{blog_info['postdate']}_img_{img_num}.jpg]"
                img_names.append(img_name)
                raw_blog_contents.append(img_name)
            elif re.search(r"se-(module|section)-text", x.attrib["class"]) is not None:
                text_list = x.xpath(".//p/span//text()")
                for text in text_list:
                    if text is not None:
                        raw_blog_contents.append(text)
                

        blog_contents = "\n".join(raw_blog_contents)
        
        blog_contents_dict["contents"] = blog_contents
        blog_contents_dict["images"] = img_names
        blog_contents_dict["image_urls"] = img_urls

        return blog_contents_dict


    # @check_execution_time
    async def parse_smarteditor_new(self, blog_body, keyword = "temp", blog_info:dict = None):
        
        for br in blog_body.findall("br"):
            br.replace_with("\n")

        blog_contents_dict = defaultdict(list)

        # 본문 내에 Image와 Text가 있는 부분만 추출

        # blog_body = blog_dom.find(".//div[@class='se_component_wrap sect_dsc __se_component_area']")
        blog_img_txt = blog_body.xpath(".//div[re:match(@class, 'se_component se_(paragraph|image) default')]", 
                                       namespaces={"re": "http://exslt.org/regular-expressions"})        

        # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
        raw_blog_contents = []
        img_urls = []
        img_names = []
        img_num = 0

        for x in blog_img_txt:
            
            if re.search(r"se_image", x.attrib["class"]) is not None:
                img_num += 1
                if "data-lazy-src" in x.find(".//img").attrib.keys():
                    img_url = x.find(".//img").attrib["data-lazy-src"]
                else:
                    img_url = x.find(".//img").attrib["src"]
                
                if img_url in img_urls:
                    continue
                else:
                    img_urls.append(img_url)

                img_name = f"[{keyword}_{blog_info['bloggername']}_{blog_info['postdate']}_img_{img_num}.jpg]"
                img_names.append(img_name)
                raw_blog_contents.append(img_name)
            elif re.search(r"se_paragraph", x.attrib["class"]) is not None:
                text_list = x.xpath(".//p[@class='se_textarea']/span//text()")
                for text in text_list:
                    if text is not None:
                        raw_blog_contents.append(text)

        blog_contents = "\n".join(raw_blog_contents)
        
        blog_contents_dict["contents"] = blog_contents
        blog_contents_dict["images"] = img_names
        blog_contents_dict["image_urls"] = img_urls

        return blog_contents_dict


    # # # @check_execution_time
    # def parse_smarteditor_2(self, blog_dom, keyword = "temp", blog_info:dict = None):
    #     for br in blog_dom.find_all("br"):
    #         br.replace_with("\n")

    #     blog_contents_dict = defaultdict(list)

    #     # 본문 내에 Image와 Text가 있는 부분만 추출

    #     blog_body = blog_dom.find(".//div[@id='postViewArea']")
    #     blog_img_txt = blog_body.findAll("p")
    #     if len(blog_img_txt) == 0:
    #         blog_img_txt = blog_body.findAll("div", attrs = {"id":re.compile(r"post-view")})

    #     # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
    #     raw_blog_contents = []
    #     img_urls = []
    #     img_names = []
    #     img_num = 0
    #     if bloggername is None:
    #         bloggername = ""
    #     else:
    #         bloggername = re.sub(r'/|\.|\*|%|\\|:|\?|\"|\'|\<|\>|\|','_',bloggername)
    #     for x in blog_img_txt:
    #         if x.find("img", attrs={"class": "_photoImage"}) is not None:
    #             img_num += 1
    #             if "data-lazy-src" in x.find("img", attrs={"class": "_photoImage"}).attrs.keys():
    #                 img_urls.append(x.find("img", attrs={"class": "_photoImage"})["data-lazy-src"])
    #             else:
    #                 img_urls.append(x.find("img", attrs={"class": "_photoImage"})["src"])
                
    #             img_name = f"[{keyword}_{bloggername}_{postdate}_img_{img_num}.jpg]"
    #             img_names.append(img_name)
    #             raw_blog_contents.append(img_name)

    #             text = x.get_text()
    #             raw_blog_contents.append(text)
    #         else:
    #             text = x.get_text()
    #             raw_blog_contents.append(text)

    #     blog_contents = "\n".join(raw_blog_contents)

    #     blog_contents_dict["images"] = img_names
    #     blog_contents_dict["image_urls"] = img_urls
    #     blog_contents_dict["contents"] = blog_contents

    #     return blog_contents_dict


    # @check_execution_time
    async def get_blog_request(self, blog_request_params):
        loop = asyncio.get_event_loop()
        # Blog URL에서 작성자, 날짜, 본문 추출
        BLOG_BASE_URL = "https://blog.naver.com/PostView.naver"
        blog_rq = requests_retry_session().get(BLOG_BASE_URL, params = blog_request_params, verify=False)
        blog_rq = await loop.run_in_executor(None, functools.partial(requests_retry_session().get, BLOG_BASE_URL, params = blog_request_params, verify=False))
        # blog_soup = BeautifulSoup(blog_rq.text, "lxml")

        return blog_rq, blog_rq.url
        

    # @check_execution_time
    async def extract_contents(self, blog_dom, keyword, blog_info:dict):

        if blog_info is None:
            blog_info = defaultdict(list)
            blog_info["bloggername"] = "temp_user"
            blog_info["postdate"] = "99999999"
        else: 
            if blog_info["bloggername"] is None:
                blog_info["bloggername"] = ""
            else:
                blog_info["bloggername"] = re.sub(r'/|\.|\*|%|\\|:|\?|\"|\'|\<|\>|\|','_',blog_info["bloggername"])


        # 블로그 본문
        if blog_dom.find(".//div[@id='postViewArea']") is not None:
            blog_type = "parse_smarteditor_2"
            blog_contents_dict = {}
            # blog_body = blog_dom.find(".//div[@id='postViewArea']")
            # blog_contents_dict = self.parse_smarteditor_2(blog_body, keyword, blog_info)

        elif blog_dom.find(".//div[@class='se-main-container']") is not None:
            blog_type = "parse_smarteditor_one"
            blog_body = blog_dom.find(".//div[@class='se-main-container']")
            blog_contents_dict = self.parse_smarteditor_one(blog_body, keyword, blog_info)
            blog_contents_dict["contents"] = re.sub(r"[\x00-\x08\x0E-\x1F\x7F]+"," ", blog_contents_dict["contents"])

        elif blog_dom.find(".//div[@class='se_component_wrap sect_dsc __se_component_area']") is not None:
            blog_type = "parse_smarteditor_new"
            blog_body = blog_dom.find(".//div[@class='se_component_wrap sect_dsc __se_component_area']")
            blog_contents_dict = self.parse_smarteditor_new(blog_body, keyword, blog_info)
            blog_contents_dict["contents"] = re.sub(r"[\x00-\x08\x0E-\x1F\x7F]+"," ", blog_contents_dict["contents"])

        else:
            blog_type = "Else"
            blog_contents_dict = {}
        
        


        return blog_contents_dict, blog_type

    def merge_dict(self, org_dict:dict, new_dict:dict, type:str = "full"):
        merged_dict = deepcopy(org_dict)
        if type == "full":
            keys = pd.unique(list(org_dict.keys()) + list(new_dict.keys()))
        elif type == "left":
            keys = list(org_dict.keys())
        elif type == "right":
            keys = list(new_dict.keys())


        for key in keys:
            if isinstance(new_dict[key], list):
                merged_dict[key].extend(new_dict[key])
            else:
                merged_dict[key].append(new_dict[key])
        
        return merged_dict

    async def get_blog_data(self, blog_info, keyword):
        self.blog_request_params = await self.create_blog_request_params(blog_info)

        blog_rq, blog_url = await self.get_blog_request(self.blog_request_params)
        blop_dom = etree.HTML(blog_rq.text)

        blog_contents_dict, blog_type = self.extract_contents(blop_dom, keyword, blog_info)
        
        if blog_contents_dict == {}:
            return None
        
        return {"blog_contents_dict" : blog_contents_dict, "blog_type" : blog_type, "blog_url" : blog_url, **blog_info}


    # @check_execution_time
    async def collect_blog(self, keywords:Union[str,list[str]], keywords_start_idx:int = 0, num_blogs = 30):
        self.result_dict = defaultdict(list)
        if not hasattr(keywords, "__iter__"):
            self.keywords = [keywords]
        else:
            self.keywords = keywords
         

        for i, keyword in enumerate(self.keywords):
            if i < keywords_start_idx:
                continue
            keyword_result_dict = defaultdict(list)
            
            self.blog_infos = self.search_blogs_by_API(keyword, num_blogs)
            if self.blog_infos is None:
                continue
            if isinstance(self.blog_infos, dict):
                self.blog_infos = [self.blog_infos]
            self.blog_infos = [blog_info for blog_info in self.blog_infos if "https://blog.naver.com" in blog_info["link"]] 
            
            print(f"{i}, keyword : {keyword}, # of blogs : {len(self.blog_infos)}")
            
            img_dir = os.path.join("./image", keyword)
            
            keyword_list = [keyword for _ in range(len(self.blog_infos))]
            futures = [asyncio.ensure_future(functools.partial(self.get_blog_data, blog_info, keyword)) for blog_info, keyword in zip(self.blog_infos, keyword_list)]
            res = await asyncio.gather(*futures)

            loop = asyncio.get_event_loop()          # 이벤트 루프를 얻음
            blog_results = loop.run_until_complete(res)          # main이 끝날 때까지 기다림

            for blog_result in blog_results:
                keyword_result_dict["keyword"].append(keyword)
                keyword_result_dict["blog_type"].append(blog_result["blog_type"])
                keyword_result_dict["title"].append(blog_result["title"])
                keyword_result_dict["writer_name"].append(blog_result["bloggername"])
                keyword_result_dict["post_date"].append(blog_result["postdate"])
                keyword_result_dict["blog_url"].append(blog_result["blog_url"])
                keyword_result_dict["contents"].append(blog_result["blog_contents_dict"]["contents"])
                keyword_result_dict["images"].append(blog_result["blog_contents_dict"]["images"])
                keyword_result_dict["image_urls"].append(blog_result["blog_contents_dict"]["image_urls"])
                # end_time = datetime.now()
                # print(f"insert dict Execution Time : {end_time - start_time}" )

            self.result_dict = self.merge_dict(org_dict = self.result_dict, new_dict = keyword_result_dict) 

            file_keyword = keyword.replace("/","_")
            with open(f"./blog_dict/{file_keyword}_blog_dict.pkl", "wb") as f:
                pickle.dump(keyword_result_dict,f)

            if (i+1) % 100 == 0:
                pass
                # pd.DataFrame(self.result_dict).to_excel(f"Naver_Blog_{i+1-100}_{i+1}.xlsx", index = False, encoding = "CP949")
                # self.result_dict = defaultdict(list)
                # pd.DataFrame(self.result_dict).to_csv(f"Naver_Blog_{i}.csvw", index = False, encoding = "CP949")
        return self.result_dict


