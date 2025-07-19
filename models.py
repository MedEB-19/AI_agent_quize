from app import db
from datetime import datetime
import json

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes = db.relationship('Quiz', backref='course', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Course {self.title}>'

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    questions_json = db.Column(db.Text, nullable=False)  # JSON string of questions
    difficulty = db.Column(db.String(20), nullable=False, default='medium')
    num_questions = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def questions(self):
        """Parse questions from JSON string"""
        try:
            return json.loads(self.questions_json)
        except:
            return []

    @questions.setter
    def questions(self, value):
        """Store questions as JSON string"""
        self.questions_json = json.dumps(value, indent=2)

    def __repr__(self):
        return f'<Quiz {self.title}>'

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)
    answers_json = db.Column(db.Text, nullable=False)  # JSON string of user answers
    score = db.Column(db.Float, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz = db.relationship('Quiz', backref='attempts')

    @property
    def answers(self):
        """Parse answers from JSON string"""
        try:
            return json.loads(self.answers_json)
        except:
            return {}

    @answers.setter
    def answers(self, value):
        """Store answers as JSON string"""
        self.answers_json = json.dumps(value)

    def __repr__(self):
        return f'<QuizAttempt {self.id}>'
