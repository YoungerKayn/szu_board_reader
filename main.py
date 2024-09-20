import logging, re
from datetime import datetime
from json import loads
from os import path
import requests as r
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from time import sleep

logging.basicConfig(level=logging.INFO, format='%(message)s')
# ========================= Configuration Part =========================
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
proxies = {'http': None, 'https': None}
board_url = 'https://www1.szu.edu.cn/board/'
login_url = 'https://authserver.szu.edu.cn/authserver/login?service=http%3A%2F%2Fwww1%2Eszu%2Eedu%2Ecn%2Fmanage%2Fcaslogin%2Easp%3Frurl%3D%252Fboard%252F'
CHROME_DRIVER_PATH = r"D:\Python\ChromeDriver\chromedriver.exe"
# ========================= Configuration Part =========================
re_type = re.compile(r'infotype=([\u4e00-\u9fa5]+)">')
re_depart = re.compile(r"\.value='([\u4e00-\u9fa5\uff08\uff09]+)'")
re_link = re.compile(r'href="view.asp\?id=([0-9]+)">')
re_title = re.compile(r'href="view.asp\?id=[0-9]+">(.+?)</a>')
re_date = re.compile(r'>([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})<')


def get_config():
    config_dir = path.join(
        path.split(path.abspath(__file__))[0], 'config.json')
    try:  # 检查配置文件是否存在
        with open(config_dir, 'r', encoding='u8') as f:
            config_file_content = f.read()
    except:  # 不存在则初始化配置文件
        with open(config_dir, 'w', encoding='u8') as f:
            config_file_content = '''\
{
    "user": "",
    "password": "",
    "push_token": "",
    "depart_select": [],
    "type_select": []
}'''
            f.write(config_file_content)
            print("Fill config.json first")
            exit()
    config = loads(config_file_content)
    return config


def get_history():
    history_dir = path.join(
        path.split(path.abspath(__file__))[0], 'history.txt')
    try:
        with open(history_dir, 'r', encoding='u8') as f:
            history = f.read().split(',')
    except:
        with open(history_dir, 'w', encoding='u8') as f:
            history = []
    return history


def write_history(history):
    history_dir = path.join(
        path.split(path.abspath(__file__))[0], 'history.txt')
    with open(history_dir, 'w', encoding='u8') as f:
        history = [i for i in history if i != '']
        for i in history:
            f.write(i + ',')


def test_cookie(cookie):
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'User-Agent': user_agent,
        "Referer": login_url,
        "Cookie": cookie
    }
    req = r.get(
        url=board_url + 'infolist.asp',
        headers=headers,
        proxies=proxies,
    )
    req.encoding = 'gb2312'
    try:
        assert "公文通" in req.text
        return True
    except:
        return False


# 获取cookie
def get_cookie(config):
    try:
        with open(path.join(path.split(path.abspath(__file__))[0], 'cookie'),
                  'r',
                  encoding='u8') as f:
            cookie = f.read()
        if test_cookie(cookie):
            print("存在有效cookie，继续使用")
            return cookie
        else:
            print("cookie失效或不存在，重新获取")
            raise Exception("cookie失效或不存在，重新获取")
    except:
        ch_options = webdriver.ChromeOptions()
        ch_options.add_experimental_option(
            "prefs", {"profile.mamaged_default_content_settings.images": 2})
        ch_options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH),
                                  options=ch_options)
        driver.get(login_url)
        driver.find_element(by=By.ID, value='username').send_keys(config['user'])
        driver.find_element(by=By.ID, value='password').click()
        sleep(3)
        driver.find_element(by=By.ID, value='password').send_keys(config['password'])
        driver.find_element(by=By.CLASS_NAME, value='m-rememberMe').click()
        driver.find_element(by=By.CLASS_NAME, value='login-btn').click()
        cookie_list = driver.get_cookies()
        cookie = cookie_list[0]["name"] + '=' + cookie_list[0]["value"]
        cookie_dir = path.join(path.split(path.abspath(__file__))[0], 'cookie')
        with open(cookie_dir, 'w', encoding='u8') as f:
            f.write(cookie)
        return cookie


def pushplus(pushplus_token,
             title,
             content,
             pushplus_topic=None,
             template=None):
    try:
        push_data = {
            "token": pushplus_token,
            "title": title,
            "content": content,
            "topic": pushplus_topic,
            "template": template
        }
        pushplus = r.post(url="http://www.pushplus.plus/send",
                          data=push_data,
                          proxies=proxies)
        result_code = loads(pushplus.text)["code"]
        if result_code == 200:
            print("pushplus success")
            global push_state
            push_state = 0
        else:
            print(f"pushplus failed: {result_code}")
    except:
        print("pushplus failed, no network connection")


class News(object):

    def __init__(self, news_link, news_title, news_date, news_type,
                 news_depart) -> None:
        self.link = news_link
        self.title = news_title
        self.date = news_date
        self.type = news_type
        self.depart = news_depart


def fetch_news(config):
    News_list = []
    cookie = get_cookie(config)
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'User-Agent': user_agent,
        "Referer": login_url,
        "Cookie": cookie
    }
    try:
        req = r.get(
            url=board_url + 'infolist.asp',
            headers=headers,
            proxies=proxies,
        )
        req.encoding = 'gb2312'
        if '公文通' not in req.text:
            print("访问公文通出错")
            pushplus(config['push_token'], 'Error', '访问公文通出错')
            exit()
    except r.exceptions.ConnectionError:
        print('Intranet Error')
        exit()

    page_content = req.text
    news_types = re_type.findall(page_content)
    news_departs = re_depart.findall(page_content)
    news_links = re_link.findall(page_content)
    news_titles = re_title.findall(page_content)
    news_dates = re_date.findall(page_content)

    for i in range(len(news_links)):
        news_link = news_links[i]
        news_title = news_titles[i]
        news_date = news_dates[i]
        news_type = news_types[i]
        news_depart = news_departs[i]
        News_list.append(News(news_link, news_title, news_date, news_type, news_depart))
    return News_list


def main():
    config = get_config()
    news_list = fetch_news(config)
    news_list_selected = []  # News to be posted
    date_now = datetime.now()
    date_format = f'{date_now.year}-{date_now.month}-{date_now.day}'  # 适配公文通的日期格式
    history = get_history()

    for news in news_list:
        if (news.link not in history and 
            news.date == date_format and 
            (not config["depart_select"] or news.depart in config["depart_select"]) and 
            (not config["type_select"] or news.type in config["type_select"])):
            news_list_selected.append(news)


    if news_list_selected == []:
        print("无新内容")
        exit()
    else:
        push_title = '公文通'
        push_content = ""
        order = 1
        for news in news_list_selected:
            history.append(news.link)
            push_content += (f"""  
{order}. [{news.title}]({board_url}view.asp?id={news.link})  
Tag:{news.type}、{news.depart}
---""")
            order += 1

    if config["push_token"]:
        pushplus(config["push_token"],
                 push_title,
                 push_content,
                 template="markdown")
    else:
        print(push_content)
    write_history(history)


if __name__ == '__main__':
    main()
