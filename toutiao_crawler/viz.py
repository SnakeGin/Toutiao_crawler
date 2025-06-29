import pymysql
import pandas as pd
import jieba
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib

# 设置中文字体
font_path = 'C:/Windows/Fonts/msyh.ttc'  # 适配你的操作系统路径
matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
matplotlib.rcParams['axes.unicode_minus'] = False

# 1. 连接数据库
conn = pymysql.connect(
    host='localhost',  # 或者你的远程数据库IP
    user='root',
    password='sjj666yyy',
    database='toutiao',
    charset='utf8mb4'
)

# 2. 读取评论数据
comments_df = pd.read_sql("SELECT text FROM comments", conn)

# 3. 分词并统计词频
all_text = ''.join(comments_df['text'].fillna('').tolist())
words = jieba.lcut(all_text)

# 去除停用词 + 非汉字词
stopwords = set(['的', '了', '是', '我', '也', '和', '就', '在', '有', '不', '人', '都', '一个', '这'])  # 可扩展
words = [
    w for w in words 
    if w.strip() and w not in stopwords and all('\u4e00' <= ch <= '\u9fa5' for ch in w) and len(w) >= 2
]

# 统计频率
word_counts = Counter(words)


# 4. 生成词云
wc = WordCloud(
    font_path=font_path,
    width=800,
    height=600,
    background_color='white'
).generate_from_frequencies(word_counts)

# 显示词云
plt.figure(figsize=(10, 7))
plt.imshow(wc, interpolation='bilinear')
plt.axis('off')
plt.title("评论词云", fontsize=20)
plt.show()
plt.savefig('comments_wordcloud.png', dpi=300, bbox_inches='tight')

# 5. 读取用户信息并排行粉丝数
users_df = pd.read_sql("SELECT distinct author_name, fans_count FROM users", conn)
users_df = users_df.dropna(subset=['fans_count']).sort_values(by='fans_count', ascending=False).head(20)

# 6. 画粉丝排行榜
plt.figure(figsize=(12, 8))
sns.barplot(
    x='fans_count',
    y='author_name',
    data=users_df,
    palette='coolwarm'
)
plt.title('粉丝数 Top 20 用户', fontsize=18)
plt.xlabel('粉丝数')
plt.ylabel('作者')
plt.tight_layout()
plt.show()
plt.savefig('fans_count_top20.png', dpi=300, bbox_inches='tight')

# 7. 关闭数据库连接
conn.close()
