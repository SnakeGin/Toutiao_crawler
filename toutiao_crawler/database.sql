CREATE DATABASE IF NOT EXISTS toutiao DEFAULT CHARSET utf8mb4;
USE toutiao;

-- 帖子信息表
CREATE TABLE IF NOT EXISTS posts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title TEXT,
    summary TEXT,
    source VARCHAR(255),
    content_type VARCHAR(50),
    url TEXT,
    create_time BIGINT,
    play_count BIGINT,
    post_id VARCHAR(50) UNIQUE
);

-- 评论信息表
CREATE TABLE IF NOT EXISTS comments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    post_id VARCHAR(50),
    comment_id VARCHAR(50) UNIQUE,
    text TEXT,
    user_id VARCHAR(50),
    user_name VARCHAR(255),
    create_time BIGINT,
    digg_count INT
);

-- 用户信息表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    author_name VARCHAR(255),
    author_url TEXT,
    fans_count INT,
    follow_count INT,
    content TEXT
);