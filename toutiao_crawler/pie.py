import pymysql
import pandas as pd
import jieba
import re
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib

# 设置中文字体
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

# 合并文本 + 分词
text = ''.join(df['summary'].dropna().tolist())
words = jieba.lcut(text)

# 停用词集合
stopwords = set(['的', '了', '是', '和', '在', '就', '也', '不', '对', '中', '上', '有', '这', '与', '及', '为', '一个', '被'])


# 只保留长度 ≥ 2 的纯中文词
def is_chinese_word(w):
    return (
        len(w) >= 2 and
        all('\u4e00' <= ch <= '\u9fa5' for ch in w) and
        w not in stopwords
    )

filtered_words = [w for w in words if is_chinese_word(w)]

# 统计词频
word_freq = Counter(filtered_words)
top10 = word_freq.most_common(10)

# 取标签和数量
labels = [w for w, c in top10]
sizes = [c for w, c in top10]

# 饼图绘制
plt.figure(figsize=(8, 8))
plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
plt.title("摘要字段 Top10 高频词分布图", fontsize=16)
plt.axis('equal')
plt.show()
plt.savefig('posts_summary_pie_chart.png', dpi=300, bbox_inches='tight')
