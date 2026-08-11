# Request
## request.Session.get(self,url: str | bytes, params: Mapping | None = None, **kwargs) -> Response
- params:URL参数
```py
session.get("https://api.com/users", params={"page":1})
# https://api.com/users?page=1
```
- kwargs:其他请求参数
```py
session.get(url, timeout = 5, headers = {
        "User-Agent":"xxx"
    }
)
```
| 参数              | 作用      |
| --------------- | ------- |
| timeout         | 超时时间    |
| headers         | 请求头     |
| cookies         | Cookie  |
| auth            | 认证      |
| verify          | SSL验证   |
| allow_redirects | 是否允许重定向 |

# with、async with
本质上是一个上下文管理器器
# urlparse(url)
```
url = "https://www.example.com/news/article?id=123#comment"
result = urlparse(url)
print(result)

ParseResult(
scheme='https',
netloc='www.example.com',
path='/news/article',
params='',
query='id=123',
fragment='comment'
)
```
# 爬虫协议
```
url:https://example.com/robots.txt

User-agent: *
Disallow: /admin/ # 禁止访问, 即禁止访问https://example.com/admin/下任何东西
Disallow: /private/
Crawl-delay: 5 # 访问间隔5s
Request-rate: 10/60 # 60s最多请求10次

User-agent: Googlebot # 只针对 Google 爬虫。
Allow: /private/public.html # 允许访问

所有爬虫不允许访问https://example.com/admin/* 、 https://example.com/private/*
但是Googlebot 允许访问https://example.com/private/public.html
```

RobotFileParser类的使用
```
rp = RobotFileParser()
rp.set_url("https://example.com/robots.txt")
rp.read()#下载并解析, 同步阻塞 IO。

allowed = rp.can_fetch("MyBot", "https://example.com/news/1") # allowed为bool类型

# 异步下载解析，rp.read()的异步版本
robots_text = await session.get("https://example.com/robots.txt").text()
rp.parse(robots_text.splitlines())

delay = rp.crawl_delay("MyBot")
rate = rp.request_rate("MyBot") # RequestRate(requests=10,seconds=60)

```
# BeautifulSoup
soup = BeautifulSoup(html, "html.parser") # html格式解析，soup 是整个 HTML 树。
第二个参数有: html.parser, lxml, html5lib
```
title = soup.find("title") # 找第一个title标签
print(title) # <title>Python教程</title>
print(title.text) # Python教程

links = soup.find_all("a") # 找所有a标签, 返回列表
print(links) # [<a href="/page1">下一页</a>, xxx]

p = soup.find("p", class_="content") # 查找标签为p, class类型为content，注意参数为class_
print(p) # [<p class="content"> Python is good</p>, xxx]
div = soup.find(id="article")
print(div) # <div id="article">正文</div>
```

# Path
prompt = self._article_agg_prompt.format(articles=joined)

# 进入项目环境
source .venv/bin/activate
pip list 查看安装包
deactivate 退出项目环境