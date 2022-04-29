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

# Hide Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NaverBlogCrawl:
    
    client_id = "VyJ4vDh18O7CVkYDCROr"
    client_secret = "pOn2vw75sv"
    
    def __init__(self):
        pass



    def search_blogs_by_API(self, keyword:str) -> dict:
        blog_infos = defaultdict(list)
        self.keyword = keyword
        # API를 통한 검색
        encText = urllib.parse.quote(self.keyword)
        url = f"https://openapi.naver.com/v1/search/blog.xml?query={encText}&display=30"

        headers = {"X-Naver-Client-Id" : self.client_id,
                   "X-Naver-Client-Secret" : self.client_secret}
        rq = requests.get(url, headers=headers, verify=False)
        html = rq.text
        html_dict = xmltodict.parse(html)

        # Blog URL들만 추출
        blog_infos["urls"] = [x["link"] for x in html_dict["rss"]["channel"]["item"] if "blog.naver" in x["link"]]
        blog_infos["bloggernames"] = [x["bloggername"] for x in html_dict["rss"]["channel"]["item"] if "blog.naver" in x["link"]]
        blog_infos["postdates"] = [x["postdate"] for x in html_dict["rss"]["channel"]["item"] if "blog.naver" in x["link"]]

        
        return blog_infos



    def find_real_url(self, url:str) -> str:
        # 실제 Url 찾기
        url_rq = requests.get(url, verify=False)

        soup = BeautifulSoup(url_rq.text, "html.parser")

        blog_url = f"https://blog.naver.com/{soup.select_one('iframe')['src']}"
        
        return blog_url



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

    

    def parse_smarteditor_one(self, blog_soup:BeautifulSoup, bloggername:str, postdate:str) -> dict:
        blog_contents_dict = defaultdict(list)

        blog_body = blog_soup.find("div", attrs={"class":"se-main-container"})

        # 본문 내에 Image와 Text가 있는 부분만 추출
        blog_img_txt = blog_body.findAll("div", attrs={"class" : [re.compile(r"se-(module|section)-text"), re.compile(r"se-(module|section)-image")]})

        # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
        raw_blog_contents = []
        img_urls = []
        img_names = []
        img_num = 0
        if bloggername is None:
            bloggername = ""
        else:
            bloggername = re.sub(r'/|\.|\*|%|\\|:|\?|\"|\'|\<|\>|\|','_',bloggername)
        for x in blog_img_txt:
            if any([re.findall(r"se-module-image|se-section-image", y) for y in x.attrs["class"]]):
                
                try: 
                    if "data-lazy-src" in x.select_one("img").attrs.keys():
                        img_url = x.select_one("img")["data-lazy-src"]
                    else:
                        img_url = x.select_one("img")["src"]
                except:
                    continue
                
                if img_url in img_urls:
                    continue
                else:
                    img_urls.append(img_url)
                
                img_num += 1
                img_name = f"{self.keyword}_{bloggername}_{postdate}_img_{img_num}.jpg"
                img_names.append(img_name)
                raw_blog_contents.append(img_name)
            elif "se-module-text" in x.attrs["class"]:
                text = x.get_text()
                raw_blog_contents.append(text)

        blog_contents = "\n".join(raw_blog_contents)
        
        blog_contents_dict["contents"] = blog_contents
        blog_contents_dict["images"] = img_names
        blog_contents_dict["image_urls"] = img_urls

        return blog_contents_dict


    def parse_smarteditor_new(self, blog_soup:BeautifulSoup, bloggername:str, postdate:str):
        blog_contents_dict = defaultdict(list)

        # 본문 내에 Image와 Text가 있는 부분만 추출
        blog_body = blog_soup.find("div", attrs = {"class":"se_component_wrap sect_dsc __se_component_area"})
        blog_img_txt = blog_body.findAll("div", attrs={"class" : ["se_component se_paragraph default", "se_component se_image default"]})

        # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
        raw_blog_contents = []
        img_urls = []
        img_names = []
        img_num = 0
        if bloggername is None:
            bloggername = ""
        else:
            bloggername = re.sub(r'/|\.|\*|%|\\|:|\?|\"|\'|\<|\>|\|','_',bloggername)
        for x in blog_img_txt:
            if "se_image" in x.attrs["class"]:
                img_num += 1
                if "data-lazy-src" in x.select_one("img").attrs.keys():
                    img_urls.append(x.select_one("img")["data-lazy-src"])
                else:
                    img_urls.append(x.select_one("img")["src"])
                
                img_name = f"{self.keyword}_{bloggername}_{postdate}_img_{img_num}.jpg"
                img_names.append(img_name)
                raw_blog_contents.append(img_name)
            elif "se_paragraph" in x.attrs["class"]:
                text = x.get_text()
                raw_blog_contents.append(text)

        blog_contents = "\n".join(raw_blog_contents)
        
        blog_contents_dict["contents"] = blog_contents
        blog_contents_dict["images"] = img_names
        blog_contents_dict["image_urls"] = img_urls

        return blog_contents_dict



    def parse_smarteditor_2(self, blog_soup:BeautifulSoup, bloggername:str, postdate:str):
        blog_contents_dict = defaultdict(list)

        # 본문 내에 Image와 Text가 있는 부분만 추출
        blog_body = blog_soup.find("div", attrs = {"id":"postViewArea"})
        blog_img_txt = blog_body.findAll("p")

        # image 파일 이름과 블로그 글을 하나의 contents로 엮어서 text 생성
        raw_blog_contents = []
        img_urls = []
        img_names = []
        img_num = 0
        if bloggername is None:
            bloggername = ""
        else:
            bloggername = re.sub(r'/|\.|\*|%|\\|:|\?|\"|\'|\<|\>|\|','_',bloggername)
        for x in blog_img_txt:
            if x.find("img", attrs={"class": "_photoImage"}) is not None:
                img_num += 1
                if "data-lazy-src" in x.find("img", attrs={"class": "_photoImage"}).attrs.keys():
                    img_urls.append(x.find("img", attrs={"class": "_photoImage"})["data-lazy-src"])
                else:
                    img_urls.append(x.find("img", attrs={"class": "_photoImage"})["src"])
                
                img_name = f"{self.keyword}_{bloggername}_{postdate}_img_{img_num}.jpg"
                img_names.append(img_name)
                raw_blog_contents.append(img_name)

                text = x.get_text()
                raw_blog_contents.append(text)
            else:
                text = x.get_text()
                raw_blog_contents.append(text)

        blog_contents = "\n".join(raw_blog_contents)

        blog_contents_dict["images"] = img_names
        blog_contents_dict["image_urls"] = img_urls
        blog_contents_dict["contents"] = blog_contents

        return blog_contents_dict



    def extract_contents(self, blog_url:str, bloggername:str, postdate:str):
        
        # Blog URL에서 작성자, 날짜, 본문 추출
        blog_rq = requests.get(blog_url, verify=False)
        blog_soup = BeautifulSoup(blog_rq.text, "html.parser")

        self.blog_soup = blog_soup
        # # 작성자 ID
        # writer_name = blog_soup.find("span", attrs = {"class" : "nick"}).get_text().replace(" ", "_")

        # # 날짜
        # post_date = blog_soup.find("span", attrs = {"class" : "se_publishDate pcol2"}).get_text().replace(" ", "")
        # post_date = re.sub("\\.|:|\s", "_", post_date)

        # 블로그 본문
        if self.blog_soup.find("div", attrs={"id" : "postViewArea"}):
            blog_contents_dict = self.parse_smarteditor_2(self.blog_soup, bloggername, postdate)
        elif self.blog_soup.find("div", attrs={"class" : "se-main-container"}):
            blog_contents_dict = self.parse_smarteditor_one(self.blog_soup, bloggername, postdate)
        elif self.blog_soup.find("div", attrs = {"class":"se_component_wrap sect_dsc __se_component_area"}):
            blog_contents_dict = self.parse_smarteditor_new(self.blog_soup, bloggername, postdate)


        return blog_contents_dict



    def collect_blog(self, keywords:Union[str,List[str]]):
        self.result_dict = defaultdict(list)
        if not isinstance(keywords, list):
            self.keywords = [keywords]
        else:
            self.keywords = keywords
        
        for keyword in self.keywords:
            self.blog_infos = self.search_blogs_by_API(keyword)
            print(f"keyword : {keyword}, # of blogs : {len(self.blog_infos['urls'])}")
            
            img_dir = os.path.join("./image", keyword)

            for i, (url, bloggername, postdate) in enumerate(zip(self.blog_infos["urls"], self.blog_infos["bloggernames"], self.blog_infos["postdates"])):
                print(i, end = ",")
                self.blog_url = self.find_real_url(url)
                self.blog_contents_dict = self.extract_contents(self.blog_url, bloggername, postdate)
                self.save_images(self.blog_contents_dict["image_urls"], self.blog_contents_dict["images"], img_dir = img_dir)
                
                self.result_dict["keyword"].append(keyword)
                self.result_dict["writer_name"].append(bloggername)
                self.result_dict["post_date"].append(postdate)
                self.result_dict["blog_url"].append(self.blog_url)
                self.result_dict["contents"].append(self.blog_contents_dict["contents"])
                self.result_dict["images"].append(self.blog_contents_dict["images"])
                self.result_dict["image_urls"].append(self.blog_contents_dict["image_urls"])
            print("", end = "\n")
        
            pd.DataFrame(self.result_dict).to_excel(f"{self.keyword}.xlsx", index = False, encoding = "CP949")
        return self.result_dict
