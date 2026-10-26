from flask import Flask, render_template, request, send_file, redirect, url_for, make_response
import os
import uuid
import shutil
import pdfkit
from docx import Document
import pandas as pd
from openpyxl import Workbook
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Ограничение на размер файла (16 MB)
# Путь к wkhtmltopdf: из переменной окружения, иначе ищем в PATH
_wkhtmltopdf = os.environ.get('WKHTMLTOPDF_PATH') or shutil.which('wkhtmltopdf') or '/usr/bin/wkhtmltopdf'
config = pdfkit.configuration(wkhtmltopdf=_wkhtmltopdf)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_session_folder(session_id):
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}.*$', session_id):
        return 'Invalid session'
    session_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'session_{session_id}')
    if not os.path.exists(session_folder):
        os.makedirs(session_folder)
    return session_folder

def delete_old_files():
    now = datetime.now()
    for session_folder in os.listdir(app.config['UPLOAD_FOLDER']):
        session_path = os.path.join(app.config['UPLOAD_FOLDER'], session_folder)
        if os.path.isdir(session_path):
            for root, dirs, files in os.walk(session_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if now - file_creation_time > timedelta(days=365):  # Удаляем файлы старше 3 дней
                        os.remove(file_path)
                        print(f"Удален файл: {file_path}")


scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_old_files, trigger="interval", hours=1)  # Проверка каждый час
scheduler.start()

@app.route('/', methods=['GET', 'POST'])
def index():
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())  

    if request.method == 'POST':
        file = request.files['file']
        if file:
            
            if get_session_folder(session_id) == 'Invalid session':
                return "Invalid session"
            else:
                session_folder = get_session_folder(session_id) 
                file_path = os.path.join(session_folder, file.filename)
                file.save(file_path)
            
                if file.filename.endswith('.docx'):
                    output_filename = file.filename.replace('.docx', '.pdf')
                    output_path = os.path.join(session_folder, output_filename)
                    convert_word_to_pdf(file_path, output_path)
                    return redirect(url_for('download_file', filename=output_filename))

                elif file.filename.endswith('.csv'):
                    output_filename = file.filename.replace('.csv', '.xlsx')
                    output_path = os.path.join(session_folder, output_filename)
                    convert_csv_to_xlsx(file_path, output_path)
                    return redirect(url_for('download_file', filename=output_filename))
    get_params = request.args
    response = make_response(render_template('index.html', params=get_params))
    response.set_cookie('session_id', session_id)
    return response

def convert_word_to_pdf(input_path, output_path):
    doc = Document(input_path)
    pdfkit.from_string('\n'.join([p.text for p in doc.paragraphs]), output_path, configuration=config)

def convert_csv_to_xlsx(input_path, output_path):
    df = pd.read_csv(input_path)
    df.to_excel(output_path, index=False)

@app.route('/download/<filename>')
def download_file(filename):
    session_id = request.cookies.get('session_id')
    if not session_id:
        return "Session not found", 404

    session_folder = get_session_folder(session_id)
    file_path = os.path.join(session_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

@app.route('/myfiles')
def my_files():
    session_id = request.cookies.get('session_id')
    if not session_id:
        files=[]
        return render_template('myfiles.html', files=files)
    if get_session_folder(session_id) == 'Invalid session':
        return "Invalid session"
    else:
        session_folder = get_session_folder(session_id)
        if os.path.exists(session_folder):
            files = os.listdir(session_folder)
        else:
            files = []

        return render_template('myfiles.html', files=files)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 404
    
if __name__ == '__main__':
    try:
        app.run()
    finally:
        scheduler.shutdown()  # Останавливаем планировщик при завершении работы приложения
