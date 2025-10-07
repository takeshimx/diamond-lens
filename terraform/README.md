# Diamond Lens - Terraform Infrastructure

このディレクトリには、Diamond LensアプリケーションのGCPインフラストラクチャをTerraformで管理するための設定が含まれています。

## 📁 ディレクトリ構成

```
terraform/
├── modules/                    # 再利用可能なTerraformモジュール
│   ├── cloud-run/             # Cloud Runサービス
│   ├── bigquery/              # BigQueryデータセット
│   ├── iam/                   # サービスアカウント・IAM権限
│   └── secrets/               # Secret Manager
├── environments/              # 環境別設定
│   ├── dev/                   # 開発環境
│   │   ├── main.tf
│   │   └── terraform.tfvars
│   └── production/            # 本番環境
│       ├── main.tf
│       └── terraform.tfvars
└── README.md
```

## 🚀 セットアップ手順

### 1. 前提条件

- Terraform >= 1.5.0
- GCP プロジェクト: `tksm-dash-test-25`
- GCP認証情報（サービスアカウントまたはgcloud CLI）
- Terraform state用のGCS bucket

### 2. GCS Bucket作成（初回のみ）

```bash
# Terraform state保存用のbucketを作成
gsutil mb -p tksm-dash-test-25 -l asia-northeast1 gs://diamond-lens-terraform-state

# バージョニングを有効化
gsutil versioning set on gs://diamond-lens-terraform-state
```

### 3. Secret Manager設定（初回のみ）

```bash
# Gemini API Keyを設定
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy=user-managed \
  --locations=asia-northeast1

# Google認証情報を設定（必要に応じて）
gcloud secrets create google-application-credentials \
  --data-file=path/to/service-account.json \
  --replication-policy=user-managed \
  --locations=asia-northeast1
```

### 4. Artifact Registry設定（初回のみ）

```bash
# Dockerイメージリポジトリを作成
gcloud artifacts repositories create diamond-lens \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Diamond Lens container images"
```

## 💻 ローカルでの実行

### Development環境

```bash
cd terraform/environments/dev

# 初期化
terraform init

# プランの確認
terraform plan

# 適用
terraform apply

# リソース削除
terraform destroy
```

### Production環境

```bash
cd terraform/environments/production

# 初期化
terraform init

# プランの確認
terraform plan

# 適用（慎重に！）
terraform apply
```

## 🔄 CI/CD統合

このプロジェクトはGitHub Actionsを使用してTerraformを自動実行します。

### ワークフロー

1. **terraform-plan.yml** - PRに対してTerraform Planを実行
   - `terraform/**` 配下の変更を検知
   - dev/production両環境のplanを実行
   - PRにコメントで結果を表示

2. **terraform-apply.yml** - mainブランチへのマージでTerraform Applyを実行
   - インフラストラクチャの適用
   - Dockerイメージのビルド
   - Cloud Runへのデプロイ

### GitHub Secrets設定

以下のSecretsをGitHubリポジトリに設定してください：

```
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
GCP_SERVICE_ACCOUNT=terraform@tksm-dash-test-25.iam.gserviceaccount.com
```

## 📊 管理されるリソース

### Cloud Run

- **Backend Service**: FastAPIアプリケーション
  - Port: 8000
  - Memory: 1Gi (production), 512Mi (dev)
  - Auto-scaling: 0-10 instances

- **Frontend Service**: React + Vite アプリケーション
  - Port: 80
  - Memory: 512Mi
  - Auto-scaling: 0-5 instances

### IAM

- `diamond-lens-backend`: Backend用サービスアカウント
  - BigQuery Data Viewer
  - BigQuery Job User
  - Secret Manager Secret Accessor

- `diamond-lens-frontend`: Frontend用サービスアカウント
  - Cloud Run Invoker

### Secret Manager

- `gemini-api-key`: Gemini API認証キー
- `google-application-credentials`: GCP認証情報

### BigQuery

- Dataset: `mlb_stats`
- Tables:
  - `fact_batting_stats_with_risp`
  - `fact_pitching_stats`
  - その他MLB統計テーブル

## 🔧 トラブルシューティング

### State Lock エラー

```bash
# State lockを強制解除（注意して使用）
terraform force-unlock LOCK_ID
```

### 既存リソースのImport

```bash
# 既存のCloud Runサービスをimport
terraform import module.backend_cloud_run.google_cloud_run_v2_service.service \
  projects/tksm-dash-test-25/locations/asia-northeast1/services/diamond-lens-backend
```

### Plan実行時のエラー

```bash
# キャッシュをクリア
rm -rf .terraform
terraform init -reconfigure
```

## 📝 運用ベストプラクティス

1. **変更前に必ずPlanを確認**
   ```bash
   terraform plan -out=tfplan
   terraform show tfplan
   ```

2. **環境変数は terraform.tfvars で管理**
   - 機密情報はSecret Managerに保存
   - tfvarsファイルはgitにコミットしない（開発用サンプルのみ）

3. **モジュールの再利用**
   - 共通設定は `modules/` で管理
   - 環境固有の設定のみ `environments/` に記述

4. **State管理**
   - GCS bucketでstate共有
   - state lockingを有効化
   - バージョニングで履歴保持

## 🔗 関連リンク

- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GCP Best Practices](https://cloud.google.com/docs/terraform/best-practices-for-terraform)
