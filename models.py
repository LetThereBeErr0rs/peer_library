from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    learning_content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'name': self.name,
            'roll_number': self.roll_number,
            'learning_content': self.learning_content,
            'file_path': self.file_path
        }
