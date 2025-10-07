# Terraform統合ガイド - 既存環境との互換性

このドキュメントでは、**既存のCloud Build CI/CD環境を維持しながら**、Terraformを段階的に導入する方法を説明します。

## 🎯 目標

- 現在の`cloudbuild.yaml`を活かす
- ダウンタイムなしでTerraformを導入
- インフラをコードで管理できるようにする

---

## 📋 現状の確認

### 現在のCI/CDフロー

```
git push → Cloud Build Trigger → cloudbuild.yaml 実行
  ↓
1. Backend Docker build → gcr.io/tksm-dash-test-25/mlb-diamond-lens-api:latest
2. Backend deploy → mlb-diamond-lens-api (Cloud Run)
3. Frontend Docker build → gcr.io/tksm-dash-test-25/mlb-diamond-lens-frontend:latest
4. Frontend deploy → mlb-diamond-lens-frontend (Cloud Run)
```

### 既存リソース

- **Backend Cloud Run**: `mlb-diamond-lens-api`
- **Frontend Cloud Run**: `mlb-diamond-lens-frontend`
- **Container Registry**: `gcr.io` (古い方式)
- **BigQuery Dataset**: `mlb_stats`
- **Secrets**: `VITE_APP_PASSWORD`, `gemini-api-key` など

---

## 🔄 統合アプローチ

### フェーズ1: Terraformで既存リソースを管理下に置く（推奨）

**メリット:**
- ダウンタイムなし
- 既存のCI/CDフローを維持
- 段階的に移行できる

**デメリット:**
- 古いContainer Registry（gcr.io）を使い続ける
- サービス名を変更できない

### フェーズ2: 新しいリソースに移行（将来的）

**メリット:**
- 最新のArtifact Registry使用
- 命名規則を統一できる
- 完全にInfrastructure as Codeになる

**デメリット:**
- 短時間のダウンタイムが発生
- DNS/URLが変わる可能性

---

## 🚀 実装手順（フェーズ1）

### ステップ1: Terraform State用バケット作成

#### Linux/Mac (Bash)

```bash
export PROJECT_ID="tksm-dash-test-25"
export REGION="asia-northeast1"

# State保存用バケット作成
gsutil mb -l ${REGION} -p ${PROJECT_ID} gs://diamond-lens-terraform-state

# バージョニング有効化（安全のため）
gsutil versioning set on gs://diamond-lens-terraform-state
```

#### Windows (PowerShell)

```powershell
# State保存用バケット作成（変数使わず直接指定が確実）
gsutil mb -l asia-northeast1 -p tksm-dash-test-25 gs://diamond-lens-terraform-state

# バージョニング有効化（安全のため）
gsutil versioning set on gs://diamond-lens-terraform-state

# 確認
gsutil ls gs://diamond-lens-terraform-state/
```

**PowerShellで変数を使う場合:**

```powershell
$PROJECT_ID = "tksm-dash-test-25"
$REGION = "asia-northeast1"

# 注意: PowerShellでは ${} は使わず $ のみ
gsutil mb -l $REGION -p $PROJECT_ID gs://diamond-lens-terraform-state
```

---

### ステップ2: 既存リソースをTerraformにImport

#### Linux/Mac (Bash)

```bash
cd terraform/environments/production

# main.tf を既存環境互換版に置き換える
mv main.tf main-new.tf
mv main-compatible.tf main.tf

# Terraform初期化
terraform init

# 既存Cloud Runサービスをimport
terraform import 'module.backend_cloud_run.google_cloud_run_v2_service.service' \
  "projects/${PROJECT_ID}/locations/${REGION}/services/mlb-diamond-lens-api"

terraform import 'module.frontend_cloud_run.google_cloud_run_v2_service.service' \
  "projects/${PROJECT_ID}/locations/${REGION}/services/mlb-diamond-lens-frontend"

# BigQueryデータセットをimport
terraform import 'module.bigquery_dataset.google_bigquery_dataset.dataset' \
  "projects/${PROJECT_ID}/datasets/mlb_analytics_dash_25"

# Secret Managerをimport
terraform import 'module.gemini_api_key.google_secret_manager_secret.secret' \
  "projects/${PROJECT_ID}/secrets/GEMINI_API_KEY"

terraform import 'module.vite_app_password.google_secret_manager_secret.secret' \
  "projects/${PROJECT_ID}/secrets/VITE_APP_PASSWORD"
```

#### Windows (PowerShell)

```powershell
# ディレクトリ移動
cd terraform\environments\production

# main.tf を既存環境互換版に置き換える
Move-Item main.tf main-new.tf
Move-Item main-compatible.tf main.tf

# Terraform初期化
terraform init

# 既存Cloud Runサービスをimport（PowerShellでは \ 不要、直接指定）
terraform import 'module.backend_cloud_run.google_cloud_run_v2_service.service' "projects/tksm-dash-test-25/locations/asia-northeast1/services/mlb-diamond-lens-api"

terraform import 'module.frontend_cloud_run.google_cloud_run_v2_service.service' "projects/tksm-dash-test-25/locations/asia-northeast1/services/mlb-diamond-lens-frontend"

# BigQueryデータセットをimport
terraform import 'module.bigquery_dataset.google_bigquery_dataset.dataset' "projects/tksm-dash-test-25/datasets/mlb_analytics_dash_25"

# Secret Managerをimport
terraform import 'module.gemini_api_key.google_secret_manager_secret.secret' "projects/tksm-dash-test-25/secrets/GEMINI_API_KEY"

terraform import 'module.vite_app_password.google_secret_manager_secret.secret' "projects/tksm-dash-test-25/secrets/VITE_APP_PASSWORD"
```

---

### ステップ3: 差分確認

```bash
# 変更がないことを確認（import成功の証拠）
terraform plan

# 理想的な出力:
# No changes. Your infrastructure matches the configuration.
```

**差分が出る場合の対処:**

軽微な差分（ラベル追加、環境変数追加、CPU表記の正規化など）であれば問題ありません。以下を確認：

- ✅ **リソースの削除・再作成がない** (`-/+`や`must be replaced`が無い)
- ✅ **既存サービス名が変わらない**
- ✅ **イメージURLが変わらない**

上記が満たされていれば次のステップへ：

```bash
terraform apply
```

`yes`と入力して適用。これで既存リソースがTerraform管理下に入ります。

---

### ステップ4: terraform apply後の確認

```bash
# 再度planを実行
terraform plan

# 今度こそ差分ゼロになるはず:
# No changes. Your infrastructure matches the configuration.
```

---

### ステップ5: cloudbuild.yaml にTerraform統合

現在の`cloudbuild.yaml`を以下のように修正：

```yaml
steps:
  # ----------------------------------------------------------------------
  # STEP 0: Terraform Plan & Apply（インフラ変更がある場合のみ実行）
  # ----------------------------------------------------------------------
  - id: 'terraform-init'
    name: 'hashicorp/terraform:1.5.0'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        cd terraform/environments/production
        terraform init -input=false

  - id: 'terraform-plan'
    name: 'hashicorp/terraform:1.5.0'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        cd terraform/environments/production
        terraform plan -input=false -out=tfplan

  - id: 'terraform-apply'
    name: 'hashicorp/terraform:1.5.0'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        cd terraform/environments/production
        # planに変更がある場合のみapply
        if terraform show -json tfplan | grep -q '"resource_changes"'; then
          terraform apply -input=false -auto-approve tfplan
        else
          echo "No infrastructure changes detected"
        fi

  # ----------------------------------------------------------------------
  # 以下、既存のDocker build/deployステップをそのまま維持
  # ----------------------------------------------------------------------
  - id: 'backend-build-image'
    name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/${PROJECT_ID}/mlb-diamond-lens-api:latest'
      - '-t'
      - 'gcr.io/${PROJECT_ID}/mlb-diamond-lens-api:${SHORT_SHA}'
      - './backend'

  # ... 残りは既存のまま ...
```

---

### ステップ6: Cloud BuildにTerraform権限を付与

#### Linux/Mac (Bash)

```bash
# Cloud BuildのサービスアカウントにTerraform実行権限を付与
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/editor"

# State bucketへのアクセス権限
gsutil iam ch \
  serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com:objectAdmin \
  gs://diamond-lens-terraform-state
```

#### Windows (PowerShell)

```powershell
# プロジェクト番号を取得
$PROJECT_NUMBER = gcloud projects describe tksm-dash-test-25 --format="value(projectNumber)"

# Cloud BuildのサービスアカウントにTerraform実行権限を付与
gcloud projects add-iam-policy-binding tksm-dash-test-25 `
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" `
  --role="roles/editor"

# State bucketへのアクセス権限
gsutil iam ch "serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com:objectAdmin" gs://diamond-lens-terraform-state
```

**PowerShellの注意点:**
- 複数行コマンドは `` ` `` (バッククォート) で継続
- 変数は `${変数名}` で展開

---

## 🔍 CI/CDフロー（統合後）

```
git push
  ↓
Cloud Build Trigger
  ↓
cloudbuild.yaml 実行
  ↓
┌─────────────────────────────────────┐
│ STEP 0: Terraform (インフラ管理)      │
│  - terraform init                   │
│  - terraform plan                   │
│  - terraform apply (変更ある場合)     │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1-3: Backend                   │
│  - Docker build                     │
│  - Push to gcr.io                   │
│  - Deploy to Cloud Run              │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 4-6: Frontend                  │
│  - Docker build                     │
│  - Push to gcr.io                   │
│  - Deploy to Cloud Run              │
└─────────────────────────────────────┘
```

---

## 🎯 各ツールの役割分担

| ツール | 管理対象 | ファイル |
|--------|---------|---------|
| **Terraform** | インフラ構成<br>- Cloud Runサービス設定<br>- IAM権限<br>- Secret Manager<br>- BigQuery | `terraform/**/*.tf` |
| **Cloud Build** | CI/CDパイプライン<br>- Dockerビルド<br>- イメージpush<br>- デプロイ実行<br>- Terraform実行 | `cloudbuild.yaml` |

### 具体例で理解する

**ケース1: Cloud RunのCPUを増やしたい**

#### Linux/Mac

```bash
# 1. Terraformファイルを編集
vim terraform/environments/production/main.tf

# cpu = "1" → cpu = "2" に変更

# 2. git push
git add terraform/
git commit -m "Increase backend CPU to 2"
git push

# 3. Cloud Buildが自動実行
#    → terraform apply でCPU設定が変更される
#    → その後Docker build/deployも実行される
```

#### Windows

```powershell
# 1. Terraformファイルを編集
notepad terraform\environments\production\main.tf
# または VSCode: code terraform\environments\production\main.tf

# cpu = "1" → cpu = "2" に変更

# 2. git push
git add terraform/
git commit -m "Increase backend CPU to 2"
git push

# 3. Cloud Buildが自動実行（同じ）
```

**ケース2: アプリケーションコードを修正**

```bash
# 1. コード修正
# 2. git push
# 3. Cloud Buildが自動実行
#    → terraform plan で変更なし（スキップ）
#    → Docker build/deployのみ実行
```

---

## ⚠️ 重要な注意点

### 1. Terraform管理下のリソースは直接変更しない

**❌ ダメな例:**
```bash
# GCPコンソールやgcloudで直接変更
gcloud run services update mlb-diamond-lens-api --memory=2Gi
```

これをやると、次回のterraform applyで設定が元に戻る！

**✅ 正しい方法:**
```bash
# Terraformファイルを編集してgit push
vim terraform/environments/production/main.tf
# memory = "2Gi" に変更
git push
```

### 2. Secretはコードに含めない

```hcl
# ❌ これは絶対ダメ！
module "gemini_api_key" {
  secret_data = "AIzaSyXXXXXX..."  # Gitにコミットされる！
}

# ✅ 正しい方法
module "gemini_api_key" {
  secret_id = "gemini-api-key"
  # secret_dataは指定しない
}
```

Secretの値はGCPコンソールまたはgcloudで設定：

#### Linux/Mac
```bash
echo -n "YOUR_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
```

#### Windows (PowerShell)
```powershell
# オプション1: ファイル経由
"YOUR_KEY" | Out-File -Encoding ASCII -NoNewline temp_secret.txt
gcloud secrets versions add gemini-api-key --data-file=temp_secret.txt
Remove-Item temp_secret.txt

# オプション2: GCPコンソールから手動設定（推奨）
```

### 3. State fileは絶対に手動編集しない

- State fileはTerraformが管理する
- 壊れると復旧が困難
- GCS bucketのバージョニングを有効にして保護

---

## 🔄 将来的な移行（フェーズ2）

現在の設定に慣れたら、以下を検討：

### 1. Artifact Registryへ移行

#### Linux/Mac
```bash
# 新しいレジストリ作成
gcloud artifacts repositories create diamond-lens \
  --repository-format=docker \
  --location=asia-northeast1

# Terraformとcloudbuild.yamlを更新
# gcr.io → asia-northeast1-docker.pkg.dev に変更
```

#### Windows (PowerShell)
```powershell
# 新しいレジストリ作成（PowerShellでは \ 不要）
gcloud artifacts repositories create diamond-lens `
  --repository-format=docker `
  --location=asia-northeast1

# 確認
gcloud artifacts repositories list
```

### 2. サービス名の統一

```bash
# 新サービスをTerraformで作成
# mlb-diamond-lens-api → diamond-lens-backend

# トラフィックを新サービスに切り替え
# 旧サービスを削除
```

---

## 💻 Windows PowerShell チートシート

| 用途 | Bash | PowerShell |
|------|------|-----------|
| 環境変数設定 | `export VAR="value"` | `$VAR = "value"` または `$env:VAR = "value"` |
| 変数使用 | `${VAR}` | `$VAR` または `${VAR}` |
| 複数行コマンド | `\` | `` ` `` (バッククォート) |
| ファイル移動 | `mv file1 file2` | `Move-Item file1 file2` |
| ディレクトリ移動 | `cd path/to/dir` | `cd path\to\dir` |
| パス区切り | `/` | `\` |

---

## 📚 FAQ

**Q: Cloud BuildとGitHub Actions、どっちを使うべき？**

A: 既にCloud Buildが動いているなら、そのまま使うのが楽。GitHub Actionsは新規プロジェクトや、GitHub中心の開発フローで有利。

**Q: Terraformでデプロイもできるの？**

A: できるが推奨しない。Terraformはインフラ管理用。デプロイ（Dockerイメージの更新）はCloud BuildやGitHub Actionsに任せる。

**Q: terraform importが失敗する**

A: リソースIDの形式を確認。以下のコマンドで正しいIDを取得：

#### Linux/Mac
```bash
gcloud run services describe mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --format="value(name)"
```

#### Windows (PowerShell)
```powershell
gcloud run services describe mlb-diamond-lens-api `
  --region=asia-northeast1 `
  --format="value(name)"
```

**Q: 既存環境を壊さずにテストしたい**

A: `dev`環境で先にテスト：

#### Linux/Mac
```bash
cd terraform/environments/dev
terraform init
terraform plan
```

#### Windows (PowerShell)
```powershell
cd terraform\environments\dev
terraform init
terraform plan
```

**Q: PowerShellで変数展開がうまくいかない**

A: PowerShellでは以下に注意：
- コマンド引数での `${VAR}` は使わず `$VAR` を使う
- ダブルクォート内では `"$VAR"` または `"${VAR}"` が使える
- 確実なのは直接値を指定すること

---

## ✅ チェックリスト

導入前に確認：

- [ ] GCS State bucket作成済み
- [ ] Cloud Buildサービスアカウントに権限付与済み
- [ ] 既存リソースをterraform importで取り込み済み
- [ ] `terraform plan`で差分ゼロを確認
- [ ] cloudbuild.yamlにTerraformステップ追加
- [ ] dev環境で動作確認済み

これで安全にTerraformを導入できます！🎉
