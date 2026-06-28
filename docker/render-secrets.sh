#!/usr/bin/env sh
# 方式 A（D-6）: env から .streamlit/secrets.toml の [auth] をレンダリングしてから
# 後続コマンド（streamlit run）へ exec する entrypoint ヘルパ。
#
# シークレットをイメージ層に焼き込まず、コンテナ起動時に env から流し込むことで
# client_secret / cookie_secret の追跡・露出を避ける。本スクリプトを ENTRYPOINT に、
# 既存の streamlit 起動コマンドを CMD（"$@"）に置く想定で書く。
#
# 必要な env（GCP 側の値を docker-compose の app.environment / .env から供給）:
#   OAUTH_COOKIE_SECRET         : Cookie 署名鍵（十分長いランダム文字列）
#   OAUTH_GOOGLE_CLIENT_ID      : GCP OAuth クライアント ID
#   OAUTH_GOOGLE_CLIENT_SECRET  : GCP OAuth クライアントシークレット
#   OAUTH_REDIRECT_URI          : 既定 http://localhost:8501/oauth2callback
#
# 配線状況: 本スクリプトは Dockerfile の ENTRYPOINT として設定済みで、CMD（streamlit
# 起動コマンド）を末尾の exec "$@" で起動する。OAUTH_* env は docker-compose.yml の
# app.environment と .env.example に定義済み。すなわち env → secrets.toml の経路は
# Dockerfile / docker-compose.yml / .env まで配線済みである。
set -eu

SECRETS_DIR=".streamlit"
SECRETS_FILE="${SECRETS_DIR}/secrets.toml"
REDIRECT_URI="${OAUTH_REDIRECT_URI:-http://localhost:8501/oauth2callback}"

# env 由来の値を TOML 基本文字列（"..."）へ安全に埋め込むためのエスケープ。
# 生の値に " や \（改行）が混じると secrets.toml の [auth] が文法破壊・値途中切断・
# 別キー注入（TOML インジェクション）を起こすため、TOML 仕様に沿ってエスケープする。
# 順序が重要: 先に \ を \\ に展開し、その後で " を \" にする（逆順だと " のために
# 入れた \ がさらに二重化されて壊れる）。最後に改行・復帰を \n / \r へ畳み込み、
# 基本文字列内に生の改行が残って文法破壊するのを防ぐ。
toml_escape() {
  # 1) sed で \ → \\、" → \" を行内置換（順序が結果を左右するため固定）。
  # 2) awk で複数行を畳み込み、行間の改行を TOML エスケープ \n に変換する。
  #    sed の N/分岐イディオムは BSD/GNU で末尾改行の扱いが分かれて壊れやすいため、
  #    可搬性のため改行畳み込みは awk に分離する。
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
    | awk 'BEGIN { ORS = "" } NR > 1 { printf "\\n" } { print }'
}

# 必須シークレットの欠如は弱い設定での起動を避けるため fail-fast で落とす。
for var in OAUTH_COOKIE_SECRET OAUTH_GOOGLE_CLIENT_ID OAUTH_GOOGLE_CLIENT_SECRET; do
  eval "value=\${${var}:-}"
  if [ -z "${value}" ]; then
    echo "render-secrets: 必須の環境変数 ${var} が未設定です。起動を中止します。" >&2
    exit 1
  fi
done

# 各値を TOML 値に埋める前にエスケープ済みの文字列へ変換する。
redirect_uri_esc="$(toml_escape "${REDIRECT_URI}")"
cookie_secret_esc="$(toml_escape "${OAUTH_COOKIE_SECRET}")"
client_id_esc="$(toml_escape "${OAUTH_GOOGLE_CLIENT_ID}")"
client_secret_esc="$(toml_escape "${OAUTH_GOOGLE_CLIENT_SECRET}")"

mkdir -p "${SECRETS_DIR}"
# 生成物は秘匿情報を含むため所有者のみ読めるパーミッションにする。
umask 077
cat > "${SECRETS_FILE}" <<EOF
[auth]
redirect_uri = "${redirect_uri_esc}"
cookie_secret = "${cookie_secret_esc}"

[auth.google]
client_id = "${client_id_esc}"
client_secret = "${client_secret_esc}"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF

exec "$@"
