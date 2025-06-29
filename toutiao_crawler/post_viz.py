import pymysql
import pandas as pd
import jieba
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib

# 中文字体设置（根据你的系统修改）
font_path = 'C:/Windows/Fonts/msyh.ttc'  # Windows 微软雅黑
matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
matplotlib.rcParams['axes.unicode_minus'] = False

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='sjj666yyy',
    database='toutiao',
    charset='utf8mb4'
)

# 读取 posts 表的 summary 字段
df = pd.read_sql("SELECT summary FROM posts", conn)
conn.close()

# 合并所有 summary 成一段文本
text = ''.join(df['summary'].dropna().tolist())

# 中文分词
words = jieba.lcut(text)

# 停用词集合
stopwords = set(['的', '了', '是', '和', '在', '就', '也', '不', '对', '中', '上', '有', '这', '与', '及', '为', '一个', '被'])

# ✅ 只保留全为中文的词
filtered_words = [
    w for w in words 
    if w.strip() and w not in stopwords and all('\u4e00' <= ch <= '\u9fa5' for ch in w)
]

# 词频统计
word_freq = Counter(filtered_words)

# 生成词云图
wc = WordCloud(
    font_path=font_path,
    width=1000,
    height=700,
    background_color='white'
).generate_from_frequencies(word_freq)

# 显示图像
plt.figure(figsize=(12, 8))
plt.imshow(wc, interpolation='bilinear')
plt.axis('off')
plt.title("帖子摘要词云图", fontsize=20)
plt.show()

# 保存为文件
wc.to_file('posts_summary_wordcloud.png')
