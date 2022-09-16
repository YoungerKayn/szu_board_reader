__author__ = 'YoungerKayn'

import re
from datetime import datetime
from json import loads
from os import path

import requests as r

# ========================= Configuration Part =========================
# ======= Normally, you don't need to edit the following config. =======

# Configuration dir (default: {main.py's path}\config.json)
config_dir = ''

# Push history dir (default: {main.py's path}\history.txt)
history_dir = ''

# UA
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'}

# proxy
proxies = {'http': None, 'https': None}

# Front page of SZU News
board_url = 'https://www1.szu.edu.cn/board/'
# ========================= Configuration Part =========================

# Default history dir
if history_dir == '':
    history_dir = path.join(path.split(
        path.abspath(__file__))[0], 'history.txt')

# Some Regular Expressions
re_type = re.compile(r"infotype=([\u4e00-\u9fa5]+)")
re_depart = re.compile(r"value='([\u4e00-\u9fa5]+)'")
re_link = re.compile(r'href="view.asp\?id=([0-9]+)">')
re_title = re.compile(r'href="view.asp\?id=[0-9]+">(.+?)</a>')
re_date = re.compile(r'>([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})<')
re_clicks = re.compile(r'title="累计点击数">([0-9]+)')


def get_config(config_dir):  # Get configuration and translate to a dict
    # Default config file dir
    if config_dir == '':
        config_dir = path.join(path.split(
            path.abspath(__file__))[0], 'config.json')

    try:  # Check if config file exists
        with open(config_dir, 'r', encoding='u8') as f:
            config_file_content = f.read()

    except:  # Init config file if it is not exist
        with open(config_dir, 'w', encoding='u8') as f:
            config_file_content = '''{
    "enable": 1,
    "clicks_limit": 0,
    "push_token": ""
}'''
            f.write(config_file_content)

    config = loads(config_file_content)

    if config['enable'] == 0:  # Power on/off
        exit()

    return config


def get_history(history_dir):  # News that have been pushed will be record in history_dir
    if datetime.now().hour == 7:  # Clean all history at 7 am
        with open(history_dir, 'w', encoding='u8') as f:
            history = []
    else:
        try:
            with open(history_dir, 'r', encoding='u8') as f:
                history = f.read().split(',')
        except:
            with open(history_dir, 'w', encoding='u8') as f:
                history = []
    return history  # Get history as a list


def main(config):
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

    # Get push history
    history = get_history(history_dir)

    # Used to match News' dates
    date_format = f'{date_now.year}-{date_now.month}-{date_now.day}'
    date_format_hour = f'{date_now.year}-{date_now.month}-{date_now.day} at {date_now.hour}'

    # Init push content
    push_title = '今日通告'
    push_content = f"""<font face="黑体" color=green size=5>时间:{date_format_hour}</font>  
"""

    for i in range(0, len(news_links)):
        # Create News Objects
        locals()[f'news{i}'] = News(i)

        # Choose news to push
        if int(locals()[f'news{i}'].clicks()) >= config['clicks_limit']:
            if locals()[f'news{i}'].date() == date_format:
                if locals()[f'news{i}'].link() not in history:
                    rank.append((i, locals()[f'news{i}'].clicks()))

    # Sort news by clicks
    rank.sort(key=lambda x: int(x[1]), reverse=True)
    rank = list(map(lambda x: x[0], rank))

    for i in rank:
        # Record News which will be pushed
        history.append(f"{locals()[f'news{i}'].link()}")

        # Markdown Format
        push_content += (f"""  
{order_num}. [{locals()[f'news{i}'].title()}]({board_url}view.asp?id={locals()[f'news{i}'].link()})  
**Tag:{locals()[f'news{i}'].type()}、{locals()[f'news{i}'].depart()}** <p align="left">点击量:{locals()[f'news{i}'].clicks()}</p>  

---""")

        order_num += 1

    if push_content == f"""<font face="黑体" color=green size=5>时间:{date_format + ' at ' + str(date_now.hour)}</font>  
""":  # This situation means nothing new was found
        push_title = '无新通告'
        push_content += '没有新内容'

    # Check if need to push by pushplus
    if config['push_token']:
        print(len(push_content))

        # Pushplus
        try:
            pushplus = r.get(
                url=f'http://www.pushplus.plus/send?token={config["push_token"]}&title={push_title}&content={push_content}&template=markdown', proxies=proxies)
            push_response = pushplus.text  # Push result

            if re.search('414', push_response):  # Data too large to push
                # print('Data is too large')
                # if exceed words limit, show top 10 news

                # Reset push content
                push_content = f"""<font face="黑体" color=green size=5>时间:{date_format + ' at ' + str(date_now.hour)}</font>  
"""

                history = []  # Reset history
                order_num = 1  # Reset order

                for u in range(10):  # Reset news

                    i = rank[u]

                    # Record News which will be pushed
                    history.append(f"{locals()[f'news{i}'].link()}")

                    # Markdown format
                    push_content += (f"""  
{order_num}. [{locals()[f'news{i}'].title()}]({board_url}view.asp?id={locals()[f'news{i}'].link()})  
**Tag:{locals()[f'news{i}'].type()}、{locals()[f'news{i}'].depart()}** <p align="left">点击量:{locals()[f'news{i}'].clicks()}</p>  

---""")
                    order_num += 1

                # Add explanation
                push_content += f'*还有{len(rank)-10}条内容因数据过多而无法全部推送*'

                # Push again
                pushplus = r.get(
                    url=f'http://www.pushplus.plus/send?token={config["push_token"]}&title={push_title}&content={push_content}&template=markdown', proxies=proxies)
                push_response = pushplus.text  # Push result
                
            print(date_format_hour + ' : ' + push_response)  # Output log
        # Fail to connect to Internet
        except:
            print('Internet disconnected')
            exit()

    else:
        print('未设置pushplus token, 不进行推送')
        # If you need to output the content, uncomment the following code
        # print(date_format_hour + '\r' + push_content)

    # Write history
    with open(history_dir, 'w', encoding='u8') as f:
        history = [i for i in history if i != '']
        for i in history:
            f.write(i+',')


if __name__ == '__main__':
    main(get_config(config_dir))