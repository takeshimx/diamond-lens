from fastapi import APIRouter, File, UploadFile, HTTPException
from google.cloud import speech
import io

router = APIRouter(prefix="/speech", tags=["Speech"])

@router.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """
    音声ファイルをテキストに変換するエンドポイント
    
    Parameters:
    - audio_file: 音声ファイル（WebM, WAV, MP3など）
    
    Returns:
    - transcript: 変換されたテキスト
    """
    try:
        # Google Cloud Speech clientの初期化
        client = speech.SpeechClient()

        # アップロードされた音声ファイルを読み込み
        audio_content = await audio_file.read()

        # Speech APIの設定
        audio = speech.RecognitionAudio(content=audio_content)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,  # WebM形式
            sample_rate_hertz=48000,  # サンプリングレート
            language_code="ja-JP",  # 日本語
            enable_automatic_punctuation=True,  # 自動句読点
            model="default",  # デフォルトモデル
        )

        # 音声認識を実行
        response = client.recognize(config=config, audio=audio)

        # 結果を取得
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript
        
        if not transcript:
            return {"transcript": "", "message": "音声認識できませんでした"}
        
        return {"transcript": transcript}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声認識エラー: {str(e)}")
    