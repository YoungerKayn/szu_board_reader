import re
from datetime import datetime, timedelta
import requests as r

# ========================= Configuration Part =========================
clicks_limit = 0  # Push the news which have clicks more than this num
push_token = 'efe5ea07bd37420a816c1c3d492c6a5f'  # Pushplus Token
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'}
proxies = {'http': None, 'https': None}
board_url = 'https://www1.szu.edu.cn/board/'
# ========================= Configuration Part =========================

# Some Regular Expressions
re_type = re.compile(r"infotype=([\u4e00-\u9fa5]+)")
re_depart = re.compile(r"value='([\u4e00-\u9fa5]+)'")
re_link = re.compile(r'href="(view.asp\?id=[0-9]+)">')
re_title = re.compile(r'href="view.asp\?id=[0-9]+">(.+?)</a>')
re_date = re.compile(r'>([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})<')
re_clicks = re.compile(r'title="累计点击数">([0-9]+)')


def main():
    try:
        req = r.get(url=board_url+'infolist.asp', headers=headers,
                    proxies=proxies, timeout=3)
    except:
        print('Intranet disconnected')
        exit()
    req.encoding = 'gb2312'
    page_content = req.text
    news_types = re_type.findall(page_content)
    news_departs = re_depart.findall(page_content)
    news_links = re_link.findall(page_content)
    news_titles = re_title.findall(page_content)
    news_dates = re_date.findall(page_content)
    news_clicks = re_clicks.findall(page_content)

    class News(object):
        def __init__(self, number) -> None:
            self.number = number

        def type(self):
            return news_types[self.number]

        def depart(self):
            return news_departs[self.number]

        def link(self):
            return news_links[self.number]

        def title(self):
            title = news_titles[self.number]
            if re.match('<|>', title):
                title = re.sub(r'<[a-zA-Z\s=/]+>', '', title)
            return title

        def date(self):
            return news_dates[self.number]

        def clicks(self):
            return news_clicks[self.number]

    order_num = 1  # Order of News
    rank = []  # News' clicks ranking
    date_now = datetime.now()

    # Used to match News' dates
    date_format = f'{date_now.year}-{date_now.month}-{date_now.day}'

    # Init content
    push = f"""<font face="黑体" color=green size=5>日期:{date_format}</font>  
"""
    for i in range(0, len(news_links)):
        locals()[f'news{i}'] = News(i)
        if int(locals()[f'news{i}'].clicks()) >= clicks_limit and locals()[f'news{i}'].date() == date_format:
            rank.append((i, locals()[f'news{i}'].clicks()))

    # Sort by clicks
    rank.sort(key=lambda x: int(x[1]), reverse=True)
    rank = list(map(lambda x: x[0], rank))

    for i in rank:
        # Markdown Format
        push += (f"""  
{order_num}. [{locals()[f'news{i}'].title()}]({board_url}{locals()[f'news{i}'].link()})  
**{locals()[f'news{i}'].type()}、{locals()[f'news{i}'].depart()}** <p align="right">点击量:{locals()[f'news{i}'].clicks()}</p>  

---""")
        order_num += 1
    try:
        pushplus = r.get(
            url=f'http://www.pushplus.plus/send?token={push_token}&title=今日通告&content={push}&template=markdown', proxies=proxies)
    except:
        print('Internet disconnected')
        exit()
    print(pushplus.text)  # Results


if __name__ == '__main__':
    main()
