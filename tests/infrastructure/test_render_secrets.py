"""docker/render-secrets.sh の TOML エスケープ（toml_escape）の回帰テスト（D-6）。

render-secrets.sh は env 値を `.streamlit/secrets.toml` の TOML 基本文字列へ埋め込む。
`"` / `\\` / 改行が生のまま入ると TOML インジェクション（値途中切断・別キー注入）で
[auth] が文法破壊される。toml_escape() は `\\`→`\\\\`・`"`→`\\"`（順序依存）・改行畳み込み
（BSD/GNU 可搬性のため awk に分離）でこれを防ぐ非自明・可搬性依存ロジックである。

ここではスクリプト実装の内部詳細ではなく観測可能な契約を固定する: スクリプトを
subprocess 実行 → 生成された secrets.toml を tomllib で再パースし、異常値が安全に
エスケープされて (a) トップレベルキーが `auth` のみ（注入不能）、(b) 各値が原文へ
ラウンドトリップ一致すること、(c) 必須 env 欠落・空文字で非ゼロ終了 fail-fast すること。
スクリプトは src/ 4 層外の運用シェルだが、エスケープの脆弱性ガードとして tests/ に置く。
"""

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RENDER_SCRIPT = _REPO_ROOT / "docker" / "render-secrets.sh"
# exec "$@" に渡す無害な終端コマンド（即時 0 終了）。
_NOOP_COMMAND = ["sh", "-c", "exit 0"]
_DEFAULT_REDIRECT_URI = "http://localhost:8501/oauth2callback"


def _valid_env() -> dict[str, str]:
    """必須 OAUTH_* が揃った最小の正常 env。"""
    return {
        "OAUTH_COOKIE_SECRET": "cookie-secret-value",
        "OAUTH_GOOGLE_CLIENT_ID": "client-id-value",
        "OAUTH_GOOGLE_CLIENT_SECRET": "client-secret-value",
        "OAUTH_REDIRECT_URI": _DEFAULT_REDIRECT_URI,
    }


def _run_render(
    env_overrides: dict[str, str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    """render-secrets.sh を隔離 cwd・指定 env で subprocess 実行する。

    親プロセスの OAUTH_* を除去し、テスト入力（env_overrides）だけを効かせる。
    """
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("OAUTH_"):
            del env[key]
    env.update(env_overrides)
    return subprocess.run(
        ["sh", str(_RENDER_SCRIPT), *_NOOP_COMMAND],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _render_and_parse(env_overrides: dict[str, str], cwd: Path) -> dict[str, object]:
    """正常レンダリング後の secrets.toml を tomllib で再パースして返す。"""
    result = _run_render(env_overrides, cwd)
    assert result.returncode == 0, result.stderr
    secrets_file = cwd / ".streamlit" / "secrets.toml"
    assert secrets_file.exists(), "secrets.toml が生成されていない"
    return tomllib.loads(secrets_file.read_text(encoding="utf-8"))


def test_normal_values_round_trip(tmp_path: Path) -> None:
    # 正常系: 通常値がそのまま [auth] / [auth.google] に展開される。
    data = _render_and_parse(_valid_env(), tmp_path)
    assert data["auth"]["redirect_uri"] == _DEFAULT_REDIRECT_URI
    assert data["auth"]["cookie_secret"] == "cookie-secret-value"
    assert data["auth"]["google"]["client_id"] == "client-id-value"
    assert data["auth"]["google"]["client_secret"] == "client-secret-value"
    assert (
        data["auth"]["google"]["server_metadata_url"]
        == "https://accounts.google.com/.well-known/openid-configuration"
    )


def test_only_auth_top_level_key_exists(tmp_path: Path) -> None:
    # トップレベルキーは auth のみ（google は auth 配下のサブテーブル）。
    data = _render_and_parse(_valid_env(), tmp_path)
    assert set(data.keys()) == {"auth"}


def test_double_quote_in_value_round_trips(tmp_path: Path) -> None:
    # 異常値 `"`: 値途中切断を起こさず原文復元する（`"`→`\"` エスケープ）。
    env = _valid_env()
    env["OAUTH_GOOGLE_CLIENT_SECRET"] = 'abc"def"ghi'
    data = _render_and_parse(env, tmp_path)
    assert data["auth"]["google"]["client_secret"] == 'abc"def"ghi'


def test_backslash_in_value_round_trips(tmp_path: Path) -> None:
    # 異常値 `\`: `\`→`\\` を先に処理する順序の回帰防止。原文復元する。
    env = _valid_env()
    env["OAUTH_GOOGLE_CLIENT_SECRET"] = r"abc\def\\ghi"
    data = _render_and_parse(env, tmp_path)
    assert data["auth"]["google"]["client_secret"] == r"abc\def\\ghi"


def test_backslash_and_quote_together_round_trip(tmp_path: Path) -> None:
    # 順序依存の核: `\` と `"` が混在しても二重エスケープ崩れせず原文復元する。
    env = _valid_env()
    env["OAUTH_GOOGLE_CLIENT_SECRET"] = r'a\b"c\"d'
    data = _render_and_parse(env, tmp_path)
    assert data["auth"]["google"]["client_secret"] == r'a\b"c\"d'


def test_newline_in_value_folds_to_single_string(tmp_path: Path) -> None:
    # 異常値 改行: \n 畳み込みで単一文字列値として原文復元する（生改行による文法破壊防止）。
    env = _valid_env()
    env["OAUTH_COOKIE_SECRET"] = "line1\nline2\nline3"
    data = _render_and_parse(env, tmp_path)
    assert data["auth"]["cookie_secret"] == "line1\nline2\nline3"


def test_injection_attempt_cannot_create_extra_key(tmp_path: Path) -> None:
    # [auth.injected] 注入試行: `"`＋改行で別テーブルを生やそうとしても不能。
    env = _valid_env()
    payload = 'x"\n[auth.injected]\nadmin = "true'
    env["OAUTH_GOOGLE_CLIENT_SECRET"] = payload
    data = _render_and_parse(env, tmp_path)
    # トップレベルは auth のみ。auth 配下にも injected は生えない。
    assert set(data.keys()) == {"auth"}
    assert "injected" not in data["auth"]
    # 注入文字列はまるごと client_secret の値として閉じ込められる。
    assert data["auth"]["google"]["client_secret"] == payload


def test_empty_redirect_uri_falls_back_to_default(tmp_path: Path) -> None:
    # 空文字 redirect: `:-` 既定により規定の oauth2callback URL に倒れる。
    env = _valid_env()
    env["OAUTH_REDIRECT_URI"] = ""
    data = _render_and_parse(env, tmp_path)
    assert data["auth"]["redirect_uri"] == _DEFAULT_REDIRECT_URI


@pytest.mark.parametrize(
    "missing_var",
    ["OAUTH_COOKIE_SECRET", "OAUTH_GOOGLE_CLIENT_ID", "OAUTH_GOOGLE_CLIENT_SECRET"],
)
def test_missing_required_env_fails_fast(missing_var: str, tmp_path: Path) -> None:
    # 必須 env 欠落: 非ゼロ終了で fail-fast し、secrets.toml を生成しない。
    env = _valid_env()
    del env[missing_var]
    result = _run_render(env, tmp_path)
    assert result.returncode != 0
    assert missing_var in result.stderr
    assert not (tmp_path / ".streamlit" / "secrets.toml").exists()


def test_empty_required_env_fails_fast(tmp_path: Path) -> None:
    # 空文字 env も未設定と同様に fail-fast する（弱い設定での起動を防ぐ）。
    env = _valid_env()
    env["OAUTH_COOKIE_SECRET"] = ""
    result = _run_render(env, tmp_path)
    assert result.returncode != 0
    assert "OAUTH_COOKIE_SECRET" in result.stderr
    assert not (tmp_path / ".streamlit" / "secrets.toml").exists()
