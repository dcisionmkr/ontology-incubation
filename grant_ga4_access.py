"""
サービスアカウントにGA4プロパティへの閲覧権限を付与するワンタイムスクリプト
実行: python grant_ga4_access.py
ブラウザが開くのでkichisinger@gmail.comでログインしてください
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

PROPERTY_ID = "540457835"
SERVICE_ACCOUNT_EMAIL = "ga4-analytics-reader@ishikettsu-analytics.iam.gserviceaccount.com"
OAUTH_CLIENT_FILE = Path(__file__).parent / "oauth_client.json"

SCOPES = ["https://www.googleapis.com/auth/analytics.manage.users"]

print("ブラウザが開きます。kichisinger@gmail.com でログインしてください...")
flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_FILE, scopes=SCOPES)
creds = flow.run_local_server(port=0)

service = build("analyticsadmin", "v1alpha", credentials=creds)

try:
    result = service.properties().accessBindings().create(
        parent=f"properties/{PROPERTY_ID}",
        body={
            "user": SERVICE_ACCOUNT_EMAIL,
            "roles": ["predefinedRoles/viewer"],
        }
    ).execute()
    print(f"✅ 権限付与完了!")
    print(f"   結果: {result}")
except Exception as e:
    print(f"❌ エラー: {e}")
