import time
from pathlib import Path
import threading
from functools import partial
import random
import json
import execjs
from lxml import etree
import os
import re
import requests
import sys
from loguru import logger
import pymysql

class Jrtt():
    def __init__(self):
        super().__init__()
        self.file_name = os.path.basename(__file__).replace('.py', '')
        self.log = self.init_logger(self.file_name)
        self.headers = {
            "Referer": "https://so.toutiao.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
        }
        self.cookies = {
            "passport_csrf_token": "51a907544865bd27a99baffcd3244b57",
            "tt_webid": "7503802936411080218",
            "_ga": "GA1.1.1804927282.1750425093",
            "_S_IPAD": "0",
            "s_v_web_id": "verify_mc4txqxw_6y5NqwHx_V4y2_4mfD_AbOr_yN8nxWLCziq1",
            "_ga_QEHZPBE5HH": "GS2.1.s1750485973$o2$g1$t1750486742$j60$l0$h0",
            # "ttwid": "1%7Cc-urFbVcMWBdXfx5EZawtNHHBmqm_Z6GS0mtTSbujZQ%7C1750486751%7C0407cbd91ab9d11efac104255f09b66722427d9b99b819e92ca5453d480aa195",
            "_S_WIN_WH": "463_844",
            "__ac_nonce": "",
            "__ac_signature": "_02B4Z6wo00f018qNPPwAAIDDCS5D-egZhRPKrThAAJr.56",
            "__ac_referer": "https://so.toutiao.com/"
        }
        #sjj add
        self.init_db()
    
    #sjj add
    def init_db(self):
        self.conn = pymysql.connect(
        host='localhost',
        user='root',
        password='sjj666yyy',
        database='toutiao',
        charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()

    @staticmethod
    def init_logger(current_file):
        log_formatting = '{time} {level} {message}'
        logger.add(f"{current_file}.log", format=log_formatting, level="INFO", rotation='00:00')
        return logger

    def get_nonce_id(self, params):
        """获取 nonce 进行加密"""
        url = "https://so.toutiao.com/search"
        response = requests.get(url, headers=self.headers, params=params)
        return response.cookies["__ac_nonce"]

    def get_search_id(self, url, cookies, params):
        """获取search_id"""
        response = requests.get(url, headers=self.headers, cookies=cookies, params=params)
        return ''.join(re.findall("logId: '(.*?)'", response.text))

    def keyword_spider(self, keyword, page):
        self.log.info(f"当前采集  {keyword}，第{page}页")
        """根据关键词到头条去搜索"""
        params = {
            "dvpf": "pc",
            "source": "pagination",
            "keyword": keyword,
            "page_num": page,
            "pd": "information",
            "action_type": "pagination",
            "from": "news",
            "cur_tab_title": "news",
            "search_id": ""
        }

        nonce_id = self.get_nonce_id(params)
        cookies = self.cookies
        cookies["__ac_nonce"] = nonce_id

        with open('toutiao_keyword.js', 'r', encoding="utf-8") as f:
            jscode = f.read()
        signtrue = execjs.compile(jscode).call('get_sign', nonce_id)  # js模拟加密signtrue

        cookies['__ac_signature'] = signtrue
        cookies[
            'ttwid'] = '1%7Cg09JEcYwHa9ll-kjRF5U_7tjVs1Azv03lOGvINq8NUY%7C1751174443%7Cd873f090003dc7d4015c7cc696ff18c7b6b4bedd3599275eab9e5a3e5ca02b69'
        url = "https://so.toutiao.com/search"

        search_id = self.get_search_id(url, cookies, params)
        print(search_id)
        params["search_id"] = search_id

        response = requests.get(url, headers=self.headers, cookies=cookies, params=params)
        #print(response.text)
        json_data = re.findall('>({"extraData".*?)</script>', response.text)
        # title  # 标题
        # summary_text  # 简略内容
        # source =  # 来源
        # content_schema_type  # 评论
        # ttsearch_msite_url  # 二级页面地址
        # create_time  # 发布时间
        # play_effective_count  # 播放次数
        datas = json.loads(json_data[0]).get("rawData", {}).get("data", [])
        if not datas:
            self.log.info("采集完毕")
            return
        for item in datas:

            ###########
            post_id = item.get("group_id", "")
            sql = """
            INSERT IGNORE INTO posts (title, summary, source, content_type, url, create_time, play_count, post_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (
                item.get('title', ''),
                item.get("emphasized", {}).get('summary', ''),
                item.get("emphasized", {}).get('source', ''),
                item.get("content_schema_type", ''),
                item.get("ttsearch_msite_url", ''),
                item.get("create_time", 0),
                item.get("play_effective_count", 0),
                post_id
            ))
            self.conn.commit()

            # 获取评论和用户
            self.comment_spider(item.get("ttsearch_msite_url", ''))
            self.spider_spider_user(item.get("ttsearch_msite_url", ''))
        

            dicts = {"title": item.get('title', ''), "summary_text": item.get("emphasized", {}).get('summary_text', ''),
                     "source": item.get("emphasized", {}).get('source', ''),
                     "content_schema_type": item.get("content_schema_type", ''),
                     "ttsearch_msite_url": item.get("ttsearch_msite_url", ''),
                     "create_time": item.get("create_time", ''),
                     "play_effective_count": item.get("play_effective_count", {})}
            self.log.info(f"{dicts['title']},{dicts['ttsearch_msite_url']}, {dicts['source']}")
        return True

    def comment_spider(self, url):
        """获取详情等评论信息"""
        """评论好像不用加密"""
        u_id = url.split('/')[4]
        url = "https://www.toutiao.com/article/v4/tab_comments/"
        params = {
            "aid": "24",
            "app_name": "toutiao_web",
            "offset": "0",
            "count": "20",
            "group_id": u_id,
            "item_id": u_id,
            "_signature": ""
        }
        cookies = {
            # "_signature": signtrue
        }
        response = requests.get(url, params=params, headers=self.headers, cookies=cookies)
        #print(response.json())
        for item in response.json()["data"]:
            #print(item)
            # 写入 comments 表
            try:
                comment_data = item.get("comment", {})
                if not comment_data:
                    self.log.warning(f"空评论数据：{item}")
                    return
                sql = """
                INSERT IGNORE INTO comments
                    (post_id, comment_id, text, user_id, user_name, create_time, digg_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                self.cursor.execute(sql, (
                    u_id,
                    comment_data.get("id", ""),
                    comment_data.get("text", ""),
                    comment_data.get("user_id", ""),
                    comment_data.get("user_name", ""),
                    comment_data.get("create_time", 0),
                    comment_data.get("digg_count", 0)
                ))
                self.conn.commit()
                self.log.info(f"评论 {item.get('comment_id', '')} 信息写入完成")
            except Exception as e:
                self.log.error(f"写入评论信息失败: {e}")
        #print(response)
        


    def get_zan(self, u):
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        url = "https://www.toutiao.com/api/pc/user/fans_stat"
        params = {
            # "_signature": "_02B4Z6wo00f01NXA1ogAAIDAFmOpj7ZWY1jV5NIAAF0uuvREHrS9Ppuv51LOHMQLxTrsQ9eenzYJI72NbdTT6t54o3drBmIvSHGgo8BC4XWLRnIrblje9wYSu74YA8JTKrYUTF4xvSjlrQZNcb"
        }
        data = {
            "token": u.split('/')[-2]
        }
        response = requests.post(url, headers=headers, params=params, data=data)
        if response.status_code != 200:
            return
        return response.json()

    def get_user_stats(self, author_url: str) -> dict:
        """
        通过用户主页 URL 拿到粉丝数和关注数，返回 {'fans': int, 'follows': int}。
        """
        token = author_url.rstrip('/').split('/')[-1]  # 直接取最后一段作为 token
        api = "https://www.toutiao.com/api/pc/user/fans_stat"
        headers = {
            "User-Agent": self.headers["User-Agent"],
        }
        data = {"token": token}
        resp = requests.post(api, headers=headers, data=data)
        if resp.status_code != 200:
            self.log.error(f"get_user_stats 接口失败 {resp.status_code}")
            return {"fans": 0, "follows": 0}

        js = resp.json().get("data", {})
        return {
            "fans": js.get("fans", 0),
            "follows": js.get("follow", 0)
        }

    def spider_spider_user(self, url):
        cookies = {
            "ttwid": ''.join(random.choice(['0', '1']) for _ in range(50))
        }
        # params = {
        # }
        # response = requests.get(url, headers=self.headers, cookies=cookies, params=params)
        # html = etree.HTML(response.text)
        # content = ''.join(html.xpath('//div[@class="article-content"]/div[2]//text()'))
        # jsdata = json.loads(''.join(re.findall('ld\+json">(.*?)</script', response.text)))
        # jsdata["content"] = content
        # u = jsdata["author"]["url"]
        # url = f'https://www.toutiao.com{u}'
        # data = self.get_zan(url)
        # if data:
        #     jsdata["data"] = data
        # print(jsdata)
        # 先拿文章页里的 JSON
        resp = requests.get(url, headers=self.headers,
                            cookies={"ttwid": ''.join(random.choice('01') for _ in range(50))})
        if resp.status_code != 200:
            self.log.error(f"文章页请求失败 {resp.status_code}")
            return

        html = etree.HTML(resp.text)
        content = ''.join(html.xpath('//div[@class="article-content"]/div[2]//text()')).strip()
        raw = ''.join(re.findall(r'ld\+json">(.*?)</script>', resp.text))
        jsdata = json.loads(raw)
        author = jsdata["author"]
        author_url = f"https://www.toutiao.com{author['url']}"

        # 拿粉丝 & 关注
        stats = self.get_user_stats(author_url)

        # 写入 users 表
        try:
            sql = """
            INSERT IGNORE INTO users
                (author_name, author_url, fans_count, follow_count)
            VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(sql, (
                author.get("name", "").strip(),
                author_url,
                stats["fans"],
                stats["follows"],
                
            ))
            self.conn.commit()
            self.log.info(f"作者 {author['name']} 信息写入完成")
        except Exception as e:
            self.log.error(f"写入作者信息失败: {e}")


    def run(self):
        """keyword_spider 关键词采集首页， 自动翻页"""
        for page in range(100000):
            result = self.keyword_spider("计算机组成", page)  # 输入keyword
            if not result:
                break

        # # """comment_spider，采集评论内容，默认采集一页，模拟ttwid不封号"""
        # url = 'https://www.toutiao.com/article/7517469025413104143/?wid=1750644306383'
        # # self.comment_spider(url)
        # #
        # """spider_spider_user，采集主页内容，不加cookie不封号"""
        # self.spider_spider_user(url)

    def main(self):
        self.run()
        self.cursor.close()
        self.conn.close()

Jrtt().main()
