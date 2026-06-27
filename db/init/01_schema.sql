-- MySQL 初回起動時に app_db 上で実行される初期化スクリプト。
-- greetings テーブルを作成し、初期メッセージを 1 行投入する。
CREATE TABLE IF NOT EXISTS greetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- 長さ 255 は src/usecase/manage_greetings_usecase.py の MAX_MESSAGE_LENGTH が
    -- 真実源。一方を変えたら必ずもう一方も同期させること。
    message VARCHAR(255) NOT NULL
);

INSERT INTO greetings (message) VALUES ('Hello, World from MySQL');
