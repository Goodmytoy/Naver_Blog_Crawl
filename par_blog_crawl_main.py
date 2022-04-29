from Naver_Blog_Crawl import *
from multiprocessing_on_dill import Pool, cpu_count
from functools import partial
# from tqdm import tqdm
import pandas as pd
import numpy as np
import sys
import os
import lxml

with open("search_keyword.pkl", "rb") as f:
    search_keywords = pickle.load(f)

num_cores = 2
search_keywords_split = np.array_split(search_keywords[:4], num_cores)

def collect_blog(keywords):
    naver_blog_crawl = NaverBlogCrawl()
    return naver_blog_crawl.collect_blog(keywords, keywords_start_idx = 0, num_blogs = 10)

with Pool(num_cores) as p:
    result = p.map(collect_blog, search_keywords_split)

with open("result_dict.pkl", "wb") as f:
    pickle.dump(result, f)