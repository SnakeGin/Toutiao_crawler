#### 项目说明文档

##### 1.环境说明

###### 	a.数据库

​		使用MySQL数据库，自主安装配置好数据库后，在终端输入指令：

​			`mysql -u root -p`

​		随后输入密码，并将database.sql代码复制到终端并回车

​		对于本项目，共设计了三个表：**帖子信息表（posts）、评论信息表（comments）、用户表（users）**

​		具体数据库表信息请见：[database.sql]()

###### 	b.python依赖库

​		使用anaconda虚拟环境，请先下载anaconda，后创建新环境，安装本项目所需的python库

​			`pip install -r requirement.txt`

###### 	c.前后端

​		前端使用html，后端基于flask框架。

##### 2.各代码说明

###### 	jrtt.py

​		爬虫代码，提供了特定（自选）主题的今日头条内容的爬取，对每个帖子的帖子号、标题、摘要、发布时间、发布人、相关评论（评论人、评论id、评论内容、评论发布时间等）以及发布人的粉丝概况等信息进行爬取。以下具体介绍

​		1. 类和初始化部分

```python
class Jrtt():
    def __init__(self):
        super().__init__()
        self.file_name = os.path.basename(__file__).replace('.py', '')
        self.log = self.init_logger(self.file_name)
        self.headers = {...}
        self.cookies = {...}
        self.init_db()
```

- 以类封装爬虫，符合面向对象设计；
- 初始化日志模块，方便后续信息记录；
- 设置请求头和cookies（固定部分 + 动态部分）；
- 初始化数据库连接（MySQL，`pymysql`），后续用于数据存储。

------

​		2.日志初始化

```python
@staticmethod
def init_logger(current_file):
    logger.add(f"{current_file}.log", format='{time} {level} {message}', level="INFO", rotation='00:00')
    return logger
```

- 使用了 `loguru` 进行日志管理，简洁且易用；
- 日志文件每日凌晨自动轮转，便于日志管理。

------

​		3.关键请求准备函数

- `get_nonce_id(params)`：访问搜索首页，获取动态 `__ac_nonce` 值，头条反爬中重要的动态参数；
- `get_search_id(url, cookies, params)`：发请求获取动态 `search_id`，在请求参数里必填，用于分页请求；
- 这些函数确保请求参数符合今日头条的动态加密要求。

​		4.核心爬取函数：`keyword_spider`

```python
def keyword_spider(self, keyword, page):
    # 构造请求参数
    params = {...}
    # 获取 nonce
    nonce_id = self.get_nonce_id(params)
    # 更新 cookies
    cookies = self.cookies
    cookies["__ac_nonce"] = nonce_id

    # 读取本地JS文件，用execjs调用js函数，生成加密签名
    with open('toutiao_keyword.js', 'r', encoding="utf-8") as f:
        jscode = f.read()
    signtrue = execjs.compile(jscode).call('get_sign', nonce_id)
    cookies['__ac_signature'] = signtrue

    # 固定更新 ttwid，防止封禁
    cookies['ttwid'] = '固定字符串'

    # 获取search_id并写入params
    search_id = self.get_search_id(url, cookies, params)
    params["search_id"] = search_id

    # 请求搜索结果
    response = requests.get(url, headers=self.headers, cookies=cookies, params=params)

    # 从html中提取json数据，并加载
    json_data = re.findall('>({"extraData".*?)</script>', response.text)
    datas = json.loads(json_data[0]).get("rawData", {}).get("data", [])

    # 数据入库 + 进一步爬取评论、作者
```

- 主要步骤：
  - 先获取必须的动态参数 `nonce_id` 和 `search_id`，通过调用本地JS动态计算加密签名，保证请求合法；
  - 访问带有cookies和headers的搜索接口，拿到搜索结果JSON；
  - 解析JSON后遍历帖子数据，写入数据库；
  - 对每条帖子调用评论爬取和作者爬取，深度爬取。

------

​	5.评论爬取：`comment_spider`

```python
def comment_spider(self, url):
    # 组装评论接口参数和请求
    u_id = url.split('/')[4]
    params = {..., "group_id": u_id, "item_id": u_id}
    response = requests.get(url, params=params, headers=self.headers)

    # 遍历评论，写入comments表
```

- 传入文章url，提取文章id后访问评论接口；
- 不需要复杂加密，直接请求，节省计算资源；
- 逐条写入评论表。

------

​	6. 作者信息爬取：`spider_spider_user`

```python
def spider_spider_user(self, url):
    # 请求文章页，解析出作者json数据
    resp = requests.get(url, headers=self.headers, cookies={"ttwid": 随机字符串})
    html = etree.HTML(resp.text)
    content = ''.join(html.xpath('//div[@class="article-content"]/div[2]//text()')).strip()
    raw = ''.join(re.findall(r'ld\+json">(.*?)</script>', resp.text))
    jsdata = json.loads(raw)
    author = jsdata["author"]

    # 访问作者粉丝数和关注数接口
    stats = self.get_user_stats(author_url)

    # 入库 users 表
```

- 通过文章页内嵌JSON获取作者信息（包括作者主页url）；
- 访问作者粉丝关注接口获取更详细数据；
- 随机生成cookie防止封禁；
- 最后写入数据库。

------

​	7. 用户粉丝和关注数接口调用

```python
def get_user_stats(self, author_url):
    token = author_url.rstrip('/').split('/')[-1]
    api = "https://www.toutiao.com/api/pc/user/fans_stat"
    data = {"token": token}
    resp = requests.post(api, headers=headers, data=data)
    ...
    return {"fans": ..., "follows": ...}
```

- 通过用户token访问官方粉丝统计接口；
- 返回粉丝和关注数；
- 方便统计分析作者影响力。

------

​	8. 运行入口与翻页

```python
def run(self):
    for page in range(100000):
        result = self.keyword_spider("操作系统", page)
        if not result:
            break
```

- 以关键词“操作系统”为例，翻页采集；
- 遇到没有数据时结束循环；
- 支持超大页数，方便深度采集。



###### 	toutiao_keywords.js

​		反爬虫脚本，具体实现：

​	1. 代码上下文初始化部分

```js
window = global;

document = {};
document.referrer = '';
document.cookie = '';
navigator = {};
navigator.userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

location = {};
location.href = ''
location.protocol = 'https:';
```

- 这里定义了模拟浏览器环境的全局变量 `window`、`document`、`navigator`、`location` 等，给了部分属性值，给了一个伪装的 User-Agent 字符串。
- 一般用于在非浏览器环境（比如Node.js）运行这段代码，或者用来欺骗检测环境。

------

​	2. 核心函数定义：`_$jsvmprt`

```js
(glb = "undefined" == typeof window ? global : window)._$jsvmprt = function(b, e, f) { ... }
```

- 这是一个赋给全局变量的函数。
- 函数参数 `b`, `e`, `f` 是外部传入的数据，`b`是一个16进制字符数组或者类似的二进制数据。
- 这个函数里包含大量的内部函数和数据解码/解析逻辑。

------

​	3. 反射与继承检测代码

```js
function a() {
    if ("undefined" == typeof Reflect || !Reflect.construct)
        return !1;
    if (Reflect.construct.sham)
        return !1;
    if ("function" == typeof Proxy)
        return !0;
    try {
        return Date.prototype.toString.call(Reflect.construct(Date, [], (function () {}))),
            !0
    } catch (b) {
        return !1
    }
}
```

- 这个函数用于检测当前运行环境是否支持`Reflect.construct`，以及`Proxy`等高级JS特性，判断JS引擎的能力。

------

​	4. 多层数据解析逻辑

```js
function l(b, e) {
    var f = b[e++];
    var a = b[e];
    var d = parseInt("" + f + a, 16);
    ...
}
```

- 这些函数实现了对16进制编码数据的解析，判断长度、偏移、内容等，作用是把二进制或16进制数据转成JS可操作的结构。

------

​	5. 动态执行代码的特征

这段代码中最关键的一点是：

- 有大量栈操作 `S[R]`，递归调用 `G` 函数，似乎是一个自定义的字节码解释器或者虚拟机。
- 通过对传入的二进制数据进行解码和执行，从而实现动态代码加载或执行。
- 结构类似某种基于栈的虚拟机，执行混淆过的字节码。



​	6.加密或混淆关键

```js
var r = 0;
...
for (P = i.q[z][0]; P < i.q[z][1]; P++)
    A += String.fromCharCode(r ^ i.p[P]);
```

- 这段代码中，`r`是一个异或掩码，对数据进行了异或操作，常用作简单的加密/混淆。
- 这种手法可以防止直接用文本方式分析代码。

------

​	7. 错误检测和防篡改

```js
if ("HNOJ@?RC" != I)
    throw new Error("error magic number " + I);
```

- 对输入的`b`数组头部有“magic number”校验，确保传入数据格式正确。
- 这也是一种防止代码被恶意修改或错误调用的机制。

| 特点                 | 说明                                         |
| -------------------- | -------------------------------------------- |
| 伪造全局浏览器环境   | 让代码在非浏览器环境能执行，或者欺骗环境判断 |
| 复杂16进制字节码解析 | 读取16进制数据，解析成指令和参数             |
| 自定义字节码解释器   | 实现类似虚拟机的运行机制，动态执行代码       |
| 异或加密混淆         | 对数据做简单异或处理，防止明文分析           |
| Magic Number 校验    | 确保数据格式正确，防止篡改                   |
| 反射与特性检测       | 判断运行环境能力，做不同处理                 |
| 动态执行代码         | 实现代码的动态加载和执行，防止静态分析       |

###### 		

###### 	pie.py、post_viz.py、times.py、viz.py

​		根据已经爬取并写入到本地数据库中的数据进行可视化分析		

###### 	crawler.py

​		为主程序设计的爬虫代码，基本与**jrtt.py**一致。实现了用户界面自定义关键词输入功能。	

###### 	app.py

​		主程序，采用了**B/S架构**，可运行特定关键字的今日头条信息爬取，在终端输入python app.py后，打开本地测试ip后，结果如下：

###### ![](D:\6220\pic\image-20250629164754825.png)

​	本代码集成了今日头条的内容爬取、对保存到本地数据库的爬虫数据的可视化分析，具体包括近30日发布的相关主题帖子的数目分析、爬取的帖子发布者的粉丝量排行信息、爬取的帖子的内容的摘要词云图、帖子评论内容的词云图。	



##### 3.具体运行

​	**无用户可视化界面运行：**

​		在终端输入`python jrtt.py`

​		 通过修改jrtt代码中的keyword的字段进行特定主题的内容爬取，具体效果如下：

```python
result = self.keyword_spider("keyword",page)
```

![](D:\6220\pic\QQ图片20250629165552.png)

​			

​		可以看到数据库中保存的爬取数据

![](D:\6220\pic\9A5@BZD349~J785CGZ8KGYR.png)



​	对爬取数据的可视化，即可直接分别运行pie.py、post_viz.py、times.py、viz.py代码即可，得到如下可视化信息：

<img src="D:\6220\pic\Figure_2.png" style="zoom:25%;" />

<img src="D:\6220\pic\posts_summary_wordcloud.png" alt="posts_summary_wordcloud" style="zoom:25%;" />

##### 	

##### 	有用户可视化界面运行：

​		在终端输入`python app.py`

​		点击本地测试ip后，输入想爬取的相关主题内容即可，具体效果如下：

![QQ图片20250629170318](D:\6220\pic\QQ图片20250629170318.png)