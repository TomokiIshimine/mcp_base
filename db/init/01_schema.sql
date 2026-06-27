-- MySQL 初回起動時に app_db 上で実行される初期化スクリプト。
-- greetings テーブルを作成し、初期メッセージを 1 行投入する。
CREATE TABLE IF NOT EXISTS greetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(255) NOT NULL
);

INSERT INTO greetings (message) VALUES ('Hello, World from MySQL');
