import os
import flask
from flask import Flask, request, render_template, redirect, url_for, flash
import torch
from transformers import pipeline
import torchaudio # Hugging Faceの多くの音声モデルで推奨
import tempfile # 一時ファイル保存用
import datetime # 年を取得するために追加

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)
app.secret_key = os.urandom(24) # flashメッセージ用に必要

# デフォルトのモデル名
DEFAULT_MODEL_NAME = "openai/whisper-base"

def get_device():
    """Helper function to determine the device."""
    if torch.cuda.is_available():
        return 0  # CUDA GPU
    # MPS (Apple Silicon GPU) のチェックをより安全に
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        # MPSが実際に機能するか簡単なテストを行うことも考慮できるが、ここでは存在確認のみ
        # try:
        #     torch.ones(1, device="mps")
        #     return "mps"
        # except RuntimeError: # MPSが利用できない場合 (例:古いmacOS)
        #     pass
        return "mps"
    return -1 # CPU

# ルートURL ("/") に対する処理
@app.route('/', methods=['GET'])
def index():
    # GETリクエスト時には、クライアント側のLocalStorageがモデル名を主に管理
    # current_model_nameは、LocalStorageから読み込まれるか、デフォルト値がJSで設定される
    current_year = datetime.datetime.now().year # 現在の年を取得
    return render_template('index.html', transcription=None, error=None, info=None, current_model_name=None, current_year=current_year)

# "/transcribe" URLに対する処理 (ファイルアップロード時)
@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    # ユーザーが指定したモデル名を取得、なければデフォルトを使用
    model_name_input = request.form.get('model_name', '').strip()
    current_year = datetime.datetime.now().year # 現在の年を取得

    if not model_name_input:
        current_model_name = DEFAULT_MODEL_NAME
        info_message = f"モデル名が指定されていません。デフォルトモデル ({DEFAULT_MODEL_NAME}) を使用します。"
    else:
        current_model_name = model_name_input
        info_message = None # モデル指定時は特にinfoメッセージなし

    # 'audio_file'という名前のファイルがリクエストに含まれているか確認
    if 'audio_file' not in request.files:
        flash_error = 'エラー: 音声ファイルがリクエストに含まれていません。'
        return render_template('index.html', transcription=None, error=flash_error, info=info_message, current_model_name=current_model_name, current_year=current_year)

    file = request.files['audio_file']

    if file.filename == '':
        flash_error = 'エラー: 音声ファイルが選択されていません。'
        return render_template('index.html', transcription=None, error=flash_error, info=info_message, current_model_name=current_model_name, current_year=current_year)

    if file:
        audio_path = None # audio_pathをtryブロックの外で初期化
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_audio_file:
                file.save(tmp_audio_file.name)
                audio_path = tmp_audio_file.name
            
            print(f"一時ファイルとして保存: {audio_path}")

            # デバイスを選択
            device = get_device()
            device_name_for_print = "CUDA GPU" if device == 0 else ("Apple MPS GPU" if device == "mps" else "CPU")
            print(f"文字起こしに使用するデバイス: {device_name_for_print}")
            
            print(f"モデル '{current_model_name}' のロードを開始します...")
            # パイプラインをリクエストごとに初期化
            current_transcriber = pipeline(
                "automatic-speech-recognition", 
                model=current_model_name,
                device=device,
                chunk_length_s=30, 
                stride_length_s=5
            )
            print(f"モデル '{current_model_name}' のロード完了。")
            
            print("文字起こし処理を開始します...")
            result = current_transcriber(audio_path, generate_kwargs={"task": "transcribe"}) 
            transcription_text = result["text"]
            print("文字起こし処理が完了しました。")
            print(f"結果: {transcription_text}")

            return render_template('index.html', transcription=transcription_text, error=None, info=info_message, current_model_name=current_model_name, current_year=current_year)

        except Exception as e:
            print(f"モデル '{current_model_name}' の処理中にエラー: {e}")
            error_message = f"モデル '{current_model_name}' の処理中にエラーが発生しました: {str(e)}"
            return render_template('index.html', transcription=None, error=error_message, info=info_message, current_model_name=current_model_name, current_year=current_year)
        
        finally:
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
                print(f"一時ファイルを削除: {audio_path}")
            
    return redirect(url_for('index')) # 通常ここには到達しないはず

# アプリケーションの実行
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
