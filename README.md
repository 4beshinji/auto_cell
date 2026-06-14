# auto_cell

iPSC 浮遊バイオリアクター培養を自動化するフィジカルAI。ドメイン中立なコアは
[`physical-ai-core`](../physical-ai-core) に置き、本リポジトリは **cell_culture ドメイン**
（プラグイン）＋ **シミュレーション**＋ **インフラ** だけを持つ。

## 位置づけ（A 層・iPSC 浮遊培養）

細胞培養自動化の3層のうち **A 層（バイオリアクタープロセス制御）** を対象。iPSC を
3D 浮遊/凝集体で量産する路線（撹拌槽 / Vertical-Wheel）。2D 接着ロボット培養（B 層）は対象外。
設計の根拠と CPP・制御戦略は計画ファイル（調査ブループリント）参照。

## 構成

```
src/auto_cell/
  plugins/cell_culture/   # DomainVertical 実装（environment/channels/events/tools/sanitizer/prompt）
sim/
  plant_model/            # Tier2: 文献 iPSC 浮遊速度論 ODE（scipy）。制御検証用プラント
infra/                    # compose / virtual_edge プロファイル（Tier1 結線）
```

## シミュレーション 2 層

- **Tier1 結線**: `infra/virtual_edge`（軽量確率生成器）。MQTT→WorldModel→ReAct→アクチュエータの結線確認のみ。
- **Tier2 制御検証**: `sim/plant_model`（**文献 ODE を scipy 再実装**）。アクチュエータ入力→センサ時系列を返す閉ループのプラント。検証基準は論文軌道（7日 ~35×10⁶ cells/mL、乳酸蓄積、DO 40%→10%）の再現。将来 COBRApy+GEM / 商用 co-sim に差替可能な IF。

## 開発

```bash
uv sync --extra dev          # physical-ai-core を editable で取り込む
uv run pytest
```

> コア（plugin 基盤・WorldModel・ReAct ループ）は physical-ai-core 側。core を直すと
> editable 参照で本 PJ に即反映される。
