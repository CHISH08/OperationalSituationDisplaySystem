from flask import Flask, render_template, send_file, request, abort
import boto3
import io
import os
import sys

app = Flask(__name__)

# Настройте клиента boto3 для работы с Yandex Storage
s3_client = boto3.client(
    's3',
    endpoint_url='https://storage.yandexcloud.net',
    region_name='ru-central1',
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_image')
def get_image():
    # Получаем параметры запроса: bucket и key
    bucket = request.args.get('bucket', 'remote-sensing-storage')
    key = request.args.get('key')
    if not key:
        abort(400, "Missing key parameter")
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read()
        # Для простоты считаем, что это jpeg; при необходимости определите MIME‑тип динамически
        return send_file(io.BytesIO(data), mimetype='image/jpeg')
    except Exception as e:
        print(e)
        abort(404)

@app.route('/local_image/<path:filename>')
def local_image(filename):
    base = '/app/datasets'   # проверьте, что именно сюда монтируется ./datasets
    filepath = os.path.join(base, filename)
    # выведем в логи, что пробует отдать Flask
    print(f"[DEBUG] local_image(): filename='{filename}' → filepath='{filepath}'", file=sys.stderr)
    if not os.path.isfile(filepath):
        print(f"[DEBUG]     not found on disk", file=sys.stderr)
        abort(404)
    return send_file(filepath)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8333)
