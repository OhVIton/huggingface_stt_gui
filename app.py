import os
import flask
from flask import Flask, request, render_template, redirect, url_for, jsonify # jsonify を追加
import torch
from transformers import pipeline
import torchaudio
import tempfile
import datetime
import uuid # UUID生成用
from celery import Celery, Task # Celery をインポート
from celery.result import AsyncResult # 結果取得用

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Celeryの設定
# RedisのURLを環境変数から取得するか、デフォルト値を設定
# 例: redis://localhost:6379/0
app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:56379/0')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:56379/0')

# Celeryインスタンスの作成
# Flaskアプリケーションのコンテキスト内でタスクが実行されるようにする
def make_celery(app_instance):
    celery_instance = Celery(
        app_instance.import_name, # Celery app name is based on Flask app's import name
        backend=app_instance.config['CELERY_RESULT_BACKEND'],
        broker=app_instance.config['CELERY_BROKER_URL']
    )
    celery_instance.conf.update(app_instance.config)

    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app_instance.app_context():
                return self.run(*args, **kwargs)

    celery_instance.Task = ContextTask
    return celery_instance

celery_app = make_celery(app)
print(f"Initialized Celery App. Broker: {celery_app.conf.broker_url}, Backend: {celery_app.conf.result_backend}")


DEFAULT_MODEL_NAME = "openai/whisper-base"

def get_device_info():
    if torch.cuda.is_available():
        return 0, "CUDA GPU"
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return "mps", "Apple MPS GPU"
    return -1, "CPU"

# ★★★ 修正点: タスクに明示的な名前を付与 ★★★
@celery_app.task(name='speech_to_text.transcribe_audio_task', bind=True) 
def process_transcription_task(self, audio_file_path, model_name):
    """Celeryタスクとして文字起こしを実行する関数"""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'モデル準備中...', 'model': model_name})
        device, device_name = get_device_info()
        print(f"Task {self.request.id}: モデル '{model_name}' をデバイス '{device_name}' でロードします。")

        transcriber = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device,
            chunk_length_s=30,
            stride_length_s=5
        )
        print(f"Task {self.request.id}: モデル '{model_name}' ロード完了。")
        self.update_state(state='PROGRESS', meta={'status': '文字起こし処理中...', 'model': model_name})
        
        print(f"Task {self.request.id}: 音声ファイル '{audio_file_path}' の文字起こしを開始します。")
        result = transcriber(audio_file_path)
        transcription_text = result["text"]
        print(f"Task {self.request.id}: 文字起こし完了 - 結果: {transcription_text[:50]}...")

        # 一時ファイルを削除
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
            print(f"Task {self.request.id}: 一時ファイル '{audio_file_path}' を削除しました。")
        
        return {'status': '処理完了', 'transcription': transcription_text, 'model': model_name, 'task_id': self.request.id}
    except Exception as e:
        print(f"Task {self.request.id}: エラー発生 - {str(e)}")
        # 一時ファイルを削除 (エラー時も)
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
            print(f"Task {self.request.id}: エラー発生後、一時ファイル '{audio_file_path}' を削除しました。")
        
        # Celeryタスクは状態を更新してエラーを伝える
        # .info にエラー情報を格納する
        self.update_state(state='FAILURE', meta={'status': 'エラー発生', 'error_message': str(e), 'model': model_name, 'task_id': self.request.id})
        # タスクが例外を再発生させると、CeleryはそれをFAILUREとして記録するが、meta情報は上書きされることがあるため、明示的にupdate_stateする
        raise # 例外を再発生させてCeleryにエラーを通知

@app.route('/', methods=['GET'])
def index():
    current_year = datetime.datetime.now().year
    return render_template('index.html', current_year=current_year)

@app.route('/submit_task', methods=['POST'])
def submit_task():
    if 'audio_file' not in request.files:
        return jsonify({'error': '音声ファイルが見つかりません。'}), 400
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません。'}), 400

    model_name = request.form.get('model_name', DEFAULT_MODEL_NAME).strip()
    if not model_name:
        model_name = DEFAULT_MODEL_NAME

    try:
        # 一時ファイルとして保存（Celeryタスクにパスを渡すため）
        temp_dir = tempfile.gettempdir()
        original_suffix = os.path.splitext(file.filename)[1]
        # ファイル名にタスクIDの一部やランダムな文字列を使い、衝突を避ける。
        # Celeryタスク内で削除するので、ここではタスクIDはまだ不明。UUIDでファイル名を生成。
        temp_filename = f"{uuid.uuid4().hex}{original_suffix}" # use hex for shorter name
        audio_path = os.path.join(temp_dir, temp_filename)
        file.save(audio_path)
        print(f"音声ファイルを一時保存: {audio_path}")

        # Celeryタスクを起動
        # process_transcription_task は明示的な名前を持つようになった
        task = process_transcription_task.delay(audio_path, model_name)
        print(f"Celeryタスクを起動しました。Task ID: {task.id}, モデル: {model_name}")
        
        return jsonify({'task_id': task.id, 'status_url': url_for('get_task_status', task_id=task.id), 'model_name_used': model_name}), 202
    except Exception as e:
        print(f"タスク投入エラー: {e}")
        return jsonify({'error': f'タスクの投入に失敗しました: {str(e)}'}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task_result = AsyncResult(task_id, app=celery_app)

    response_data = {
        'task_id': task_id,
        'state': task_result.state,
    }
    if task_result.state == 'PENDING':
        response_data['status_message'] = 'タスクは待機中です。'
    elif task_result.state == 'PROGRESS':
        response_data.update(task_result.info or {}) # .info は辞書であることを期待
        if 'status' not in response_data: # Ensure status_message key
             response_data['status_message'] = '処理中です...'
        else:
            response_data['status_message'] = response_data['status'] # Use status from .info
    elif task_result.state == 'SUCCESS':
        result = task_result.get() 
        response_data.update(result or {})
        if 'status' not in response_data:
            response_data['status_message'] = '処理完了'
        else:
            response_data['status_message'] = response_data['status']
    elif task_result.state == 'FAILURE':
        # .info にはタスク内で self.update_state で設定した meta が入る
        # Tracebackは task_result.traceback で取得可能
        response_data.update(task_result.info or {})
        if 'error_message' not in response_data:
            response_data['status_message'] = 'エラーが発生しました。'
            response_data['error'] = str(task_result.info) # Fallback if error_message not in info
        else:
            response_data['status_message'] = response_data.get('status', 'エラー発生')
            response_data['error'] = response_data['error_message']

    # Ensure model key exists, falling back to what might be in task_result.info
    if 'model' not in response_data and isinstance(task_result.info, dict):
        response_data['model'] = task_result.info.get('model', 'N/A')
    elif 'model' not in response_data:
        response_data['model'] = 'N/A'


    return jsonify(response_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=58080, debug=True)
