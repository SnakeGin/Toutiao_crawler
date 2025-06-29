from flask import Flask, render_template, request, jsonify
from crawler import crawl_by_keyword
import pandas as pd
import pymysql
from wordcloud import WordCloud
import jieba
from collections import Counter
import threading
import os

app = Flask(__name__)

crawl_status = {'status': 'idle'}

def get_conn():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='sjj666yyy',
        database='toutiao',
        charset='utf8mb4'
    )

def generate_comment_wordcloud():
    conn = get_conn()
    df = pd.read_sql("SELECT text FROM comments", conn)
    conn.close()
    text = ''.join(df['text'].fillna('').tolist())
    words = jieba.lcut(text)
    stopwords = set(['的','了','是','我','也','和','就','在','有','不','人','都','一个','这'])
    words = [w for w in words if w.strip() and all('一' <= ch <= '龥' for ch in w) and w not in stopwords]
    freq = Counter(words)
    wc = WordCloud(font_path='C:/Windows/Fonts/msyh.ttc', background_color='white', width=800, height=600)
    wc.generate_from_frequencies(freq).to_file('static/wordcloud.png')

def generate_summary_wordcloud():
    conn = get_conn()
    df = pd.read_sql("SELECT summary FROM posts", conn)
    conn.close()
    text = ''.join(df['summary'].fillna('').tolist())
    words = jieba.lcut(text)
    stopwords = set(['的','了','是','我','也','和','就','在','有','不','人','都','一个','这'])
    words = [w for w in words if w.strip() and all('一' <= ch <= '龥' for ch in w) and w not in stopwords]
    freq = Counter(words)
    wc = WordCloud(font_path='C:/Windows/Fonts/msyh.ttc', background_color='white', width=800, height=600)
    wc.generate_from_frequencies(freq).to_file('static/summary_wordcloud.png')

def run_crawler(keyword):
    crawl_status['status'] = 'running'
    try:
        crawl_by_keyword(keyword)
        generate_comment_wordcloud()
        generate_summary_wordcloud()
        crawl_status['status'] = 'done'
    except Exception as e:
        crawl_status['status'] = 'error'
        crawl_status['error_msg'] = str(e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_crawl', methods=['POST'])
def start_crawl():
    keyword = request.json.get('keyword')
    if crawl_status['status'] == 'running':
        return jsonify({'message': '爬虫正在运行中，请稍后'}), 429
    crawl_thread = threading.Thread(target=run_crawler, args=(keyword,))
    crawl_thread.start()
    return jsonify({'message': '爬虫启动成功'}), 202

@app.route('/crawl_status')
def check_status():
    return jsonify(crawl_status)

@app.route('/api/post_time_distribution')
def post_time_distribution():
    conn = get_conn()
    df = pd.read_sql("SELECT create_time FROM posts", conn)
    conn.close()
    df['datetime'] = pd.to_datetime(df['create_time'], unit='s')
    df['date'] = df['datetime'].dt.date.astype(str)
    stats = df['date'].value_counts().sort_index().reset_index()
    stats.columns = ['date', 'post_count']
    return jsonify(stats.to_dict(orient='records'))

@app.route('/api/top_fans')
def top_fans():
    conn = get_conn()
    df = pd.read_sql("SELECT author_name, fans_count FROM users", conn)
    conn.close()
    df = df.dropna(subset=['fans_count']).sort_values(by='fans_count', ascending=False).head(20)
    return jsonify(df.to_dict(orient='records'))

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)
