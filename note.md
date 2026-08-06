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
