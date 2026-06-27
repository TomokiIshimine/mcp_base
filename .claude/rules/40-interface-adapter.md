---
paths:
  - "src/interface_adapter/**/*.py"
---

# interface_adapter 層の規約

外界（Streamlit UI）と usecase を仲介する層。framework 依存をここに閉じ込める。

## 責務分離

- controller は入力を受けて usecase 呼び出しへ変換する。view は usecase の出力を
  表示へ整形する。両者の責務を混在させない。
- ビジネスロジックを持たない。判断は usecase/domain にあり、この層は変換と表示に
  徹する。

## framework の封じ込め

- Streamlit への依存はこの層に閉じる。Streamlit のオブジェクト・型を usecase や
  domain へ渡さない。

## 依存

- usecase を呼び出す。`infrastructure` を直接触らない（具象の結線は合成ルート）。

## 変換

- UI 入力（文字列・選択値）を usecase の入力へ検証・変換する。
- domain オブジェクトを表示用の形（境界 DTO）へ整形する。表示専用 DTO と domain
  エンティティの構造が重複しても、変更理由が異なるため統合せず別物として扱う。

## 例外

- usecase 層の業務例外（`GreetingError` 系）を捕捉し、ユーザー向け提示用の例外
  （基底 `OperationError`／利用者起因 `InvalidOperationError`・システム障害
  `SystemFailureError`）へ翻訳して提示する。スタックトレースや内部詳細を画面に
  露出しない。

## ロギング

- 操作失敗は controller が記録する（利用者起因＝WARNING、システム障害＝ERROR）。
  これが失敗の記録責務であり、同じ失敗を下位層と二重に記録しない。
