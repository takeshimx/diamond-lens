# Terraform & CI/CD セットアップガイド

このドキュメントでは、Diamond LensプロジェクトにTerraformとCI/CDを統合するための詳細な手順を説明します。

## 📋 目次

1. [初期セットアップ](#初期セットアップ)
2. [GitHub設定](#github設定)
3. [GCP設定](#gcp設定)
4. [初回デプロイ](#初回デプロイ)
5. [運用フロー](#運用フロー)

---

## 🎯 初期セットアップ

### 1. GCP Terraform State Bucket作成

```bash
# プロジェクト設定
export PROJECT_ID="tksm-dash-test-25"
export REGION="asia-northeast1"

# GCS bucket作成（Terraform state用）
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://diamond-lens-terraform-state

# バージョニング有効化
gsutil versioning set on gs://diamond-lens-terraform-state

# オブジェクトライフサイクル設定（オプション）
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "numNewerVersions": 5
        }
      }
    ]
  }
}
EOF
gsutil lifecycle set lifecycle.json gs://diamond-lens-terraform-state
```

### 2. Artifact Registry作成

```bash
# Dockerリポジトリ作成
gcloud artifacts repositories create diamond-lens \
  --repository-format=docker \
  --location=${REGION} \
  --project=${PROJECT_ID} \
  --description="Diamond Lens container images"

# 確認
gcloud artifacts repositories list --project=${PROJECT_ID}
```

### 3. Secret Manager設定

```bash
# Secret Manager APIを有効化
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Gemini API Keyを設定
read -s GEMINI_API_KEY
echo -n "${GEMINI_API_KEY}" | gcloud secrets create gemini-api-key \
  --project=${PROJECT_ID} \
  --data-file=- \
  --replication-policy=user-managed \
  --locations=${REGION}

# Google認証情報を設定（サービスアカウントJSONファイル）
gcloud secrets create google-application-credentials \
  --project=${PROJECT_ID} \
  --data-file=./service-account-key.json \
  --replication-policy=user-managed \
  --locations=${REGION}

# 確認
gcloud secrets list --project=${PROJECT_ID}
```

---

## 🔐 GitHub設定

### 1. Workload Identity Federation設定

GitHub ActionsがGCPにアクセスできるようWorkload Identity Federationを設定します。

```bash
# プロジェクト番号取得
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

# Workload Identity Pool作成
gcloud iam workload-identity-pools create github-actions \
  --project=${PROJECT_ID} \
  --location=global \
  --display-name="GitHub Actions Pool"

# Workload Identity Provider作成
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project=${PROJECT_ID} \
  --location=global \
  --workload-identity-pool=github-actions \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# サービスアカウント作成
gcloud iam service-accounts create github-actions-terraform \
  --project=${PROJECT_ID} \
  --display-name="GitHub Actions Terraform"

# サービスアカウントに権限付与
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Workload Identity Federationバインディング
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-terraform@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=${PROJECT_ID} \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository/YOUR_GITHUB_USERNAME/diamond-lens"
```

**⚠️ 重要**: `YOUR_GITHUB_USERNAME` を実際のGitHubユーザー名に置き換えてください。

### 2. GitHub Secrets設定

GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定：

```
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/providers/github-provider
GCP_SERVICE_ACCOUNT=github-actions-terraform@tksm-dash-test-25.iam.gserviceaccount.com
```

取得方法：

```bash
# Workload Identity Provider URIを取得
gcloud iam workload-identity-pools providers describe github-provider \
  --project=${PROJECT_ID} \
  --location=global \
  --workload-identity-pool=github-actions \
  --format="value(name)"

# 出力例:
# projects/123456789/locations/global/workloadIdentityPools/github-actions/providers/github-provider
```

---

## 🚀 初回デプロイ

### 1. 既存リソースのImport（既存環境がある場合）

```bash
cd terraform/environments/production

# 初期化
terraform init

# 既存リソースをimport
terraform import module.backend_cloud_run.google_cloud_run_v2_service.service \
  projects/${PROJECT_ID}/locations/${REGION}/services/diamond-lens-backend

terraform import module.frontend_cloud_run.google_cloud_run_v2_service.service \
  projects/${PROJECT_ID}/locations/${REGION}/services/diamond-lens-frontend

terraform import module.bigquery_dataset.google_bigquery_dataset.dataset \
  projects/${PROJECT_ID}/datasets/mlb_stats
```

### 2. Terraform Plan確認

```bash
# 変更内容を確認
terraform plan

# 問題なければ適用
terraform apply
```

### 3. 初回Docker Imageビルド

```bash
# 認証設定
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Backend
cd ../../backend
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/backend:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/backend:latest

# Frontend
cd ../frontend
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/frontend:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/frontend:latest
```

---

## 🔄 運用フロー

### 通常の開発フロー

1. **フィーチャーブランチで開発**
   ```bash
   git checkout -b feature/new-feature
   # コード変更
   git add .
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

2. **Pull Request作成**
   - GitHub上でPR作成
   - `terraform-plan.yml` が自動実行され、Terraform Planの結果がコメントで表示される
   - コードレビュー

3. **Merge to main**
   - PRをmainブランチにマージ
   - `terraform-apply.yml` が自動実行される
   - Terraform Apply → Docker Build → Cloud Run Deploy

### Infrastructure変更フロー

1. **Terraformコード変更**
   ```bash
   # 例: Backend CPUを増加
   vim terraform/environments/production/main.tf
   ```

2. **ローカルでテスト**
   ```bash
   cd terraform/environments/production
   terraform init
   terraform plan
   ```

3. **PR作成 & レビュー**
   - GitHub Actionsが自動でPlanを実行
   - 変更内容を確認

4. **本番適用**
   - mainにマージ
   - 自動でApply

### 緊急時の手動デプロイ

```bash
# 特定のサービスだけ再デプロイ
gcloud run deploy diamond-lens-backend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/backend:latest \
  --region=${REGION}

# または特定のバージョンにロールバック
gcloud run deploy diamond-lens-backend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/diamond-lens/backend:COMMIT_SHA \
  --region=${REGION}
```

---

## 📊 モニタリング

### ログ確認

```bash
# Cloud Runログ
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=diamond-lens-backend" \
  --limit 50 \
  --format json

# Terraform実行ログ
# GitHub Actions > Workflows > Terraform Apply で確認
```

### コスト確認

```bash
# Cloud Run コスト
gcloud beta billing projects describe ${PROJECT_ID}

# リソース使用状況
gcloud monitoring dashboards list
```

---

## 🛠️ トラブルシューティング

### State Lock解除

```bash
cd terraform/environments/production
terraform force-unlock LOCK_ID
```

### Secret更新

```bash
# 新しいバージョンを作成
echo -n "NEW_API_KEY" | gcloud secrets versions add gemini-api-key \
  --project=${PROJECT_ID} \
  --data-file=-

# Cloud Runサービスを再起動して反映
gcloud run services update diamond-lens-backend --region=${REGION}
```

### Docker Build失敗

```bash
# ローカルでビルドテスト
docker build -t test-image -f backend/Dockerfile ./backend

# ログ確認
docker logs CONTAINER_ID
```

---

## 📚 参考リンク

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions for GCP](https://github.com/google-github-actions)

---

## ✅ チェックリスト

初回セットアップ完了後、以下を確認：

- [ ] GCS bucket作成済み
- [ ] Artifact Registry作成済み
- [ ] Secret Manager設定済み
- [ ] Workload Identity Federation設定済み
- [ ] GitHub Secrets設定済み
- [ ] Terraform init成功
- [ ] 初回Docker image push成功
- [ ] Cloud Run サービスデプロイ成功
- [ ] CI/CDパイプライン動作確認

お疲れ様でした！🎉
