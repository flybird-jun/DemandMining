# Hacker News API

## 概述

我们与 [Firebase](https://firebase.google.com/) 合作，将 Hacker News 的公开数据以近乎实时的方式提供给开发者。Firebase 可以很方便地从 [Android](https://firebase.google.com/docs/android/setup)、[iOS](https://firebase.google.com/docs/ios/setup) 和 [Web](https://firebase.google.com/docs/web/setup) 接入，[服务端](https://firebase.google.com/docs/server/setup) 同样可以使用。

如果你能够使用众多 [Firebase 客户端库](https://firebase.google.com/docs/libraries/) 中的某一个，强烈建议你使用。这些库能够高效地处理网络请求，并且在数据发生变化时可以触发事件。值得一试。

如果发现任何 bug，请发送邮件至 api@ycombinator.com。

## URI 与版本管理

我们希望随着时间推移不断改进 API。变更并不总是向后兼容的，因此我们将引入版本管理。本版本的所有 URI 都以 `https://hacker-news.firebaseio.com/v0/` 为前缀，结构如下所述。目前**没有速率限制**。

出于版本管理目的，只有移除非可选字段或修改已有字段才会被视为不兼容变更。*客户端应当优雅地处理意料之外的额外字段，直接忽略即可。*

## 设计

v0 API 本质上是内存中数据结构的网络化导出。我们清楚，内存中运行良好的东西放到网络上就不那么理想了。许多“奇怪”的地方只是 HN 内部工作方式的直接映射。想要知道一篇文章的总评论数？遍历整棵评论树自己数。想看某个 item 的子评论？先加载这个 item 拿到子评论 ID，再依次加载它们。最新的页面？从 `maxid` 开始往前遍历，只保留顶级 stories。Ask、Show 等同理。

我说这些并不是要为它辩护——它确实不是理想的公开 API，但这是我们在有限时间内能够发布的版本。虽然使用上有些别扭，但基于它实现 HN 的绝大部分功能是可行的。

## Items

Stories、comments、jobs、Ask HN，甚至 polls 都统称为 **item**。它们通过唯一的整数 ID 进行标识，访问路径为 `/v0/item/<id>.json`。

所有 item 都包含下面这些字段中的若干个，**加粗**的为必填字段：

| 字段 | 描述 |
|------|------|
| **id** | item 的唯一 ID。 |
| deleted | 如果 item 已被删除，则为 `true`。 |
| type | item 类型，取值为 `"job"`、`"story"`、`"comment"`、`"poll"` 或 `"pollopt"` 之一。 |
| by | item 作者的用户名。 |
| time | item 的创建时间，使用 [Unix 时间](http://en.wikipedia.org/wiki/Unix_time) 表示。 |
| text | 评论、story 或 poll 的文本内容（HTML 格式）。 |
| dead | 如果 item 已“阵亡”，则为 `true`。 |
| parent | 该评论的父节点，可以是另一条评论，也可以是所属的 story。 |
| poll | 该 pollopt 所关联的 poll。 |
| kids | 该 item 的评论 ID 列表，按展示顺序排序。 |
| url | story 的 URL。 |
| score | story 的得分，或 pollopt 的票数。 |
| title | story、poll 或 job 的标题（HTML 格式）。 |
| parts | pollopt 关联的候选项列表，按展示顺序排序。 |
| descendants | 对于 story 或 poll，表示其下评论的总数。 |

示例 — 一个 story：https://hacker-news.firebaseio.com/v0/item/8863.json?print=pretty

```javascript
{
  "by" : "dhouston",
  "descendants" : 71,
  "id" : 8863,
  "kids" : [ 8952, 9224, 8917, 8884, 8887, 8943, 8869, 8958, 9005, 9671, 8940, 9067, 8908, 9055, 8865, 8881, 8872, 8873, 8955, 10403, 8903, 8928, 9125, 8998, 8901, 8902, 8907, 8894, 8878, 8870, 8980, 8934, 8876 ],
  "score" : 111,
  "time" : 1175714200,
  "title" : "My YC app: Dropbox - Throw away your USB drive",
  "type" : "story",
  "url" : "http://www.getdropbox.com/u/2/screencast.html"
}
```

示例 — 一条评论：https://hacker-news.firebaseio.com/v0/item/2921983.json?print=pretty

```javascript
{
  "by" : "norvig",
  "id" : 2921983,
  "kids" : [ 2922097, 2922429, 2924562, 2922709, 2922573, 2922140, 2922141 ],
  "parent" : 2921506,
  "text" : "Aw shucks, guys ... you make me blush with your compliments.<p>Tell you what, Ill make a deal: I'll keep writing if you keep reading. K?",
  "time" : 1314211127,
  "type" : "comment"
}
```

示例 — 一个 Ask HN：https://hacker-news.firebaseio.com/v0/item/121003.json?print=pretty

```javascript
{
  "by" : "tel",
  "descendants" : 16,
  "id" : 121003,
  "kids" : [ 121016, 121109, 121168 ],
  "score" : 25,
  "text" : "<i>or</i> HN: the Next Iteration<p>I get the impression that with Arc being released a lot of people who never had time for HN before are suddenly dropping in more often. (PG: what are the numbers on this? I'm envisioning a spike.)<p>Not to say that isn't great, but I'm wary of Diggification. Between links comparing programming to sex and a flurry of gratuitous, ostentatious  adjectives in the headlines it's a bit concerning.<p>80% of the stuff that makes the front page is still pretty awesome, but what's in place to keep the signal/noise ratio high? Does the HN model still work as the community scales? What's in store for (++ HN)?",
  "time" : 1203647620,
  "title" : "Ask HN: The Arc Effect",
  "type" : "story"
}
```

示例 — 一个 job：https://hacker-news.firebaseio.com/v0/item/192327.json?print=pretty

```javascript
{
  "by" : "justin",
  "id" : 192327,
  "score" : 6,
  "text" : "Justin.tv is the biggest live video site online. We serve hundreds of thousands of video streams a day, and have supported up to 50k live concurrent viewers. Our site is growing every week, and we just added a 10 gbps line to our colo. Our unique visitors are up 900% since January.<p>There are a lot of pieces that fit together to make Justin.tv work: our video cluster, IRC server, our web app, and our monitoring and search services, to name a few. A lot of our website is dependent on Flash, and we're looking for talented Flash Engineers who know AS2 and AS3 very well who want to be leaders in the development of our Flash.<p>Responsibilities<p><pre><code>    * Contribute to product design and implementation discussions\n    * Implement projects from the idea phase to production\n    * Test and iterate code before and after production release \n</code></pre>\nQualifications<p><pre><code>    * You should know AS2, AS3, and maybe a little be of Flex.\n    * Experience building web applications.\n    * A strong desire to work on website with passionate users and ideas for how to improve it.\n    * Experience hacking video streams, python, Twisted or rails all a plus.\n</code></pre>\nWhile we're growing rapidly, Justin.tv is still a small, technology focused company, built by hackers for hackers. Seven of our ten person team are engineers or designers. We believe in rapid development, and push out new code releases every week. We're based in a beautiful office in the SOMA district of SF, one block from the caltrain station. If you want a fun job hacking on code that will touch a lot of people, JTV is for you.<p>Note: You must be physically present in SF to work for JTV. Completing the technical problem at <a href=\"http://www.justin.tv/problems/bml\" rel=\"nofollow\">http://www.justin.tv/problems/bml</a> will go a long way with us. Cheers!",
  "time" : 1210981217,
  "title" : "Justin.tv is looking for a Lead Flash Engineer!",
  "type" : "job",
  "url" : ""
}
```

示例 — 一个 poll：https://hacker-news.firebaseio.com/v0/item/126809.json?print=pretty

```javascript
{
  "by" : "pg",
  "descendants" : 54,
  "id" : 126809,
  "kids" : [ 126822, 126823, 126993, 126824, 126934, 127411, 126888, 127681, 126818, 126816, 126854, 127095, 126861, 127313, 127299, 126859, 126852, 126882, 126832, 127072, 127217, 126889, 127535, 126917, 126875 ],
  "parts" : [ 126810, 126811, 126812 ],
  "score" : 46,
  "text" : "",
  "time" : 1204403652,
  "title" : "Poll: What would happen if News.YC had explicit support for polls?",
  "type" : "poll"
}
```

示例 — 该 poll 的一个候选项：https://hacker-news.firebaseio.com/v0/item/160705.json?print=pretty

```javascript
{
  "by" : "pg",
  "id" : 160705,
  "poll" : 160704,
  "score" : 335,
  "text" : "Yes, ban them; I'm tired of seeing Valleywag stories on News.YC.",
  "time" : 1207886576,
  "type" : "pollopt"
}
```

## Users

用户通过大小写敏感的 ID 进行标识，访问路径为 `/v0/user/`。只有在站点上有公开活动（评论或投稿）的用户才能通过 API 访问到。

| 字段 | 描述 |
|------|------|
| **id** | 用户的唯一用户名，**大小写敏感**。必填。 |
| **created** | 用户的创建时间，使用 [Unix 时间](http://en.wikipedia.org/wiki/Unix_time) 表示。 |
| **karma** | 用户的 karma 值。 |
| about | 用户可选的自我介绍（HTML 格式）。 |
| submitted | 用户发布的 story、poll 和 comment 的 ID 列表。 |

示例：https://hacker-news.firebaseio.com/v0/user/jl.json?print=pretty

```javascript
{
  "about" : "This is a test",
  "created" : 1173923446,
  "id" : "jl",
  "karma" : 2937,
  "submitted" : [ 8265435, 8168423, 8090946, 8090326, 7699907, 7637962, 7596179, 7596163, 7594569, 7562135, 7562111, 7494708, 7494171, 7488093, 7444860, 7327817, 7280290, 7278694, 7097557, 7097546, 7097254, 7052857, 7039484, 6987273, 6649999, 6649706, 6629560, 6609127, 6327951, 6225810, 6111999, 5580079, 5112008, 4907948, 4901821, 4700469, 4678919, 3779193, 3711380, 3701405, 3627981, 3473004, 3473000, 3457006, 3422158, 3136701, 2943046, 2794646, 2482737, 2425640, 2411925, 2408077, 2407992, 2407940, 2278689, 2220295, 2144918, 2144852, 1875323, 1875295, 1857397, 1839737, 1809010, 1788048, 1780681, 1721745, 1676227, 1654023, 1651449, 1641019, 1631985, 1618759, 1522978, 1499641, 1441290, 1440993, 1436440, 1430510, 1430208, 1385525, 1384917, 1370453, 1346118, 1309968, 1305415, 1305037, 1276771, 1270981, 1233287, 1211456, 1210688, 1210682, 1194189, 1193914, 1191653, 1190766, 1190319, 1189925, 1188455, 1188177, 1185884, 1165649, 1164314, 1160048, 1159156, 1158865, 1150900, 1115326, 933897, 924482, 923918, 922804, 922280, 922168, 920332, 919803, 917871, 912867, 910426, 902506, 891171, 807902, 806254, 796618, 786286, 764412, 764325, 642566, 642564, 587821, 575744, 547504, 532055, 521067, 492164, 491979, 383935, 383933, 383930, 383927, 375462, 263479, 258389, 250751, 245140, 243472, 237445, 229393, 226797, 225536, 225483, 225426, 221084, 213940, 213342, 211238, 210099, 210007, 209913, 209908, 209904, 209903, 170904, 165850, 161566, 158388, 158305, 158294, 156235, 151097, 148566, 146948, 136968, 134656, 133455, 129765, 126740, 122101, 122100, 120867, 120492, 115999, 114492, 114304, 111730, 110980, 110451, 108420, 107165, 105150, 104735, 103188, 103187, 99902, 99282, 99122, 98972, 98417, 98416, 98231, 96007, 96005, 95623, 95487, 95475, 95471, 95467, 95326, 95322, 94952, 94681, 94679, 94678, 94420, 94419, 94393, 94149, 94008, 93490, 93489, 92944, 92247, 91713, 90162, 90091, 89844, 89678, 89498, 86953, 86109, 85244, 85195, 85194, 85193, 85192, 84955, 84629, 83902, 82918, 76393, 68677, 61565, 60542, 47745, 47744, 41098, 39153, 38678, 37741, 33469, 12897, 6746, 5252, 4752, 4586, 4289 ]
}
```

## 实时数据

Firebase 最酷的地方在于它支持变更通知。虽然你可以单独订阅 item 和用户资料，但要观察首页排名的变化、新增 item 以及新用户，则需要使用下面的接口。

### Max Item ID

当前最大的 item ID 位于 `/v0/maxitem`。你可以从这里反向遍历以发现所有 item。

示例：https://hacker-news.firebaseio.com/v0/maxitem.json?print=pretty

```javascript
9130260
```

### New、Top 和 Best Stories

最多 500 条 top 和 new stories 在 `/v0/topstories`（其中包含 job）和 `/v0/newstories` 中获取。Best stories 在 `/v0/beststories` 中获取。

示例：https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty

```javascript
[ 9129911, 9129199, 9127761, 9128141, 9128264, 9127792, 9129248, 9127092, 9128367, ..., 9038733 ]
```

### Ask、Show 和 Job Stories

最多 200 条最新的 Ask HN、Show HN 和 Job stories 分别在 `/v0/askstories`、`/v0/showstories` 和 `/v0/jobstories` 中获取。

示例：https://hacker-news.firebaseio.com/v0/askstories.json?print=pretty

```javascript
[ 9127232, 9128437, 9130049, 9130144, 9130064, 9130028, 9129409, 9127243, 9128571, ..., 9120990 ]
```

### 变更的 Items 和 Profiles

发生变化的 item 和 profile 在 `/v0/updates` 中获取。

示例：https://hacker-news.firebaseio.com/v0/updates.json?print=pretty

```javascript
{
  "items" : [ 8423305, 8420805, 8423379, 8422504, 8423178, 8423336, 8422717, 8417484, 8423378, 8423238, 8423353, 8422395, 8423072, 8423044, 8423344, 8423374, 8423015, 8422428, 8423377, 8420444, 8423300, 8422633, 8422599, 8422408, 8422928, 8394339, 8421900, 8420902, 8422087 ],
  "profiles" : [ "thefox", "mdda", "plinkplonk", "GBond", "rqebmm", "neom", "arram", "mcmancini", "metachris", "DubiousPusher", "dochtman", "kstrauser", "biren34", "foobarqux", "mkehrt", "nathanm412", "wmblaettler", "JoeAnzalone", "rcconf", "johndbritton", "msie", "cktsai", "27182818284", "kevinskii", "wildwood", "mcherm", "naiyt", "matthewmcg", "joelhaus", "tshtf", "MrZongle2", "Bogdanp" ]
}
```