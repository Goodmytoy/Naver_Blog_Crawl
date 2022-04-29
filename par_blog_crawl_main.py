from Naver_Blog_Crawl import *
from multiprocessing_on_dill import Pool, cpu_count
from functools import partial
# from tqdm import tqdm
import pandas as pd
import numpy as np
import sys
import os
import lxml
import sys

current_dir = sys.argv[0]
num = int(sys.argv[1])
split_num = int(sys.argv[2])

with open(f"search_keywords.pkl", "rb") as f:
    search_keywords = pickle.load(f)

split_keywords = np.array_split(search_keywords, split_num)

naver_blog_crawl = NaverBlogCrawl()
naver_blog_crawl.collect_blog(split_keywords[num-1], keywords_start_idx = 0, num_blogs = 100, executor=num)