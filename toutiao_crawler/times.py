import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta

# 设置中文字体
font_path = 'C:/Windows/Fonts/msyh.ttc'
matplotlib.rcParams['font.family'] = 'Microsoft YaHei'
matplotlib.rcParams['axes.unicode_minus'] = False

# 连接数据库读取create_time
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='sjj666yyy',
    database='toutiao',
    charset='utf8mb4'
)
sql = "SELECT create_time, title FROM posts WHERE title LIKE '%坤%';"
df = pd.read_sql(sql, conn)
conn.close()

# 时间戳转datetime（秒级）
df['datetime'] = pd.to_datetime(df['create_time'], unit='s')

# 取最近30天数据
end_date = df['datetime'].max().normalize()
start_date = end_date - timedelta(days=30)  # 最近30天包括end_date当天
mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
df_recent = df.loc[mask]

# 按日期统计发帖数
df_recent['date'] = df_recent['datetime'].dt.date
post_counts = df_recent.groupby('date').size().reset_index(name='post_count')

# 如果某些日期没有数据，补全日期和0
all_dates = pd.date_range(start=start_date, end=end_date)
post_counts = post_counts.set_index('date').reindex(all_dates.date, fill_value=0).rename_axis('date').reset_index()

# 画图
plt.figure(figsize=(12, 5))
plt.bar(post_counts['date'], post_counts['post_count'], color='cornflowerblue')
plt.xticks(rotation=45)
plt.xlabel('日期')
plt.ylabel('发帖数量')
plt.title('有关蔡徐坤的帖子发帖数量（最近30天）', fontsize=16)
plt.tight_layout()
plt.show()
