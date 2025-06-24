import os
import json

def initialize_google_credentials():
    """
    從環境變數讀取 JSON 憑證內容，寫入臨時檔案，
    並設定 GOOGLE_APPLICATION_CREDENTIALS 環境變數。
    這是所有 Google Cloud 函式庫的標準驗證方法。
    """
    # 從 Railway 環境變數讀取完整的 JSON 字串
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    # 如果環境變數存在
    if creds_json_str:
        try:
            # 在 Railway 的臨時目錄 /tmp/ 中建立一個憑證檔案
            # 這是伺服器環境下處理金鑰檔案的安全做法
            temp_creds_path = "/tmp/google_creds.json"
            with open(temp_creds_path, "w") as f:
                f.write(creds_json_str)
            
            # 設定標準的 Google 環境變數，指向我們剛剛建立的臨時檔案
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
        except Exception as e:
            print(f"Google認証JSONの書き込み中にエラーが発生しました: {e}")
            raise
    else:
        # 如果未在 Railway 設定，則引發錯誤，提醒用戶
        raise ValueError("環境変数 'GOOGLE_CREDENTIALS_JSON' が設定されていません。")
