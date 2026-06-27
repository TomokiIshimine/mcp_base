-- MySQL 初回起動時に app_db 上で実行される初期化スクリプト。
-- greetings テーブルを作成し、初期メッセージを 1 行投入する。
-- utf8mb4 を明示し、VARCHAR(255) を「255 文字」として確定させる（サーバ既定の
-- 文字セットに左右されないようにする）。これにより MySQL の 255 文字制約と
-- アプリ側の MAX_MESSAGE_LENGTH（= len() による文字数判定）の意味が一致する。
CREATE TABLE IF NOT EXISTS greetings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- 長さ 255 は src/usecase/manage_greetings_usecase.py の MAX_MESSAGE_LENGTH が
    -- 真実源。一方を変えたら必ずもう一方も同期させること。アプリ検証をすり抜けても
    -- この制約が最後の砦となり、違反は infrastructure 層で利用者向けエラーへ翻訳される。
    message VARCHAR(255) NOT NULL
) DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

INSERT INTO greetings (message) VALUES ('Hello, World from MySQL');
