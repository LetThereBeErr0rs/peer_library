import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from models import db, Content

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

@app.route('/')
def home():
    return render_template('base.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/content_upload', methods=['POST'])
def content_upload():
    title = request.form.get('title')
    name = request.form.get('name')
    roll_number = request.form.get('roll_number')
    learning_content = request.form.get('learning_content')
    file = request.files.get('file')
    
    file_path = None
    if file and file.filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        file_path = file.filename 

    if title and name and roll_number and learning_content:
        new_content = Content(
            title=title, 
            name=name, 
            roll_number=roll_number, 
            learning_content=learning_content,
            file_path=file_path
        )
        db.session.add(new_content)
        db.session.commit()
    
    return redirect(url_for('home'))

@app.route('/view')
def view_content():
    search_query = request.args.get('search_query')
    if search_query:
        contents = Content.query.filter_by(roll_number=search_query).all()
    else:
        contents = []

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json':
        return jsonify([content.to_dict() for content in contents])
        
    return render_template('base.html', contents=contents, search_query=search_query)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)