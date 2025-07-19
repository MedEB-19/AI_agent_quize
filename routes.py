from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from app import app, db
from models import Course, Quiz, QuizAttempt
from quiz_generator import QuizGenerator
from content_processor import ContentProcessor
import json
import logging
import time

# Initialize components
quiz_generator = QuizGenerator()
content_processor = ContentProcessor()

@app.route('/')
def index():
    """Home page with course input form"""
    courses = Course.query.order_by(Course.created_at.desc()).limit(10).all()
    return render_template('index.html', courses=courses)

@app.route('/upload_course', methods=['POST'])
def upload_course():
    """Handle course content upload"""
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title or not content:
            flash('Please provide both course title and content.', 'error')
            return redirect(url_for('index'))
        
        # Validate content length
        if len(content) < 100:
            flash('Course content is too short. Please provide at least 100 characters.', 'error')
            return redirect(url_for('index'))
        
        # Process and validate content
        processed_content = content_processor.process_content(content)
        if not processed_content:
            flash('Unable to process the course content. Please check the format and try again.', 'error')
            return redirect(url_for('index'))
        
        # Save course to database
        course = Course(title=title, content=processed_content)
        db.session.add(course)
        db.session.commit()
        
        flash(f'Course "{title}" uploaded successfully!', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
        
    except Exception as e:
        logging.error(f"Error uploading course: {str(e)}")
        flash('An error occurred while uploading the course. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Display course details and quiz generation options"""
    course = Course.query.get_or_404(course_id)
    recent_quizzes = Quiz.query.filter_by(course_id=course_id).order_by(Quiz.created_at.desc()).limit(5).all()
    return render_template('index.html', course=course, recent_quizzes=recent_quizzes)

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    """Generate a new quiz from course content"""
    try:
        course_id = request.form.get('course_id', type=int)
        num_questions = request.form.get('num_questions', 5, type=int)
        difficulty = request.form.get('difficulty', 'medium')
        question_types = request.form.getlist('question_types')
        
        if not course_id:
            flash('Course ID is required.', 'error')
            return redirect(url_for('index'))
        
        course = Course.query.get_or_404(course_id)
        
        # Validate parameters
        if num_questions < 1 or num_questions > 20:
            flash('Number of questions must be between 1 and 20.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))
        
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
        
        if not question_types:
            question_types = ['multiple_choice', 'true_false', 'short_answer']
        
        # Generate quiz questions
        questions = quiz_generator.generate_quiz(
            course.content, 
            num_questions=num_questions,
            difficulty=difficulty,
            question_types=question_types
        )
        
        if not questions:
            flash('Unable to generate quiz questions. Please check your course content and try again.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))
        
        # Create and save quiz
        quiz_title = f"{course.title} - Quiz ({difficulty.title()})"
        quiz = Quiz(
            course_id=course_id,
            title=quiz_title,
            difficulty=difficulty,
            num_questions=len(questions)
        )
        quiz.questions = questions
        
        db.session.add(quiz)
        db.session.commit()
        
        flash(f'Quiz generated successfully with {len(questions)} questions!', 'success')
        return redirect(url_for('take_quiz', quiz_id=quiz.id))
        
    except Exception as e:
        logging.error(f"Error generating quiz: {str(e)}")
        flash('An error occurred while generating the quiz. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    """Display quiz for taking"""
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_display.html', quiz=quiz)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    """Handle quiz submission and scoring"""
    try:
        quiz_id = request.form.get('quiz_id', type=int)
        if not quiz_id:
            flash('Quiz ID is required.', 'error')
            return redirect(url_for('index'))
        
        quiz = Quiz.query.get_or_404(quiz_id)
        
        # Collect answers
        answers = {}
        for key, value in request.form.items():
            if key.startswith('question_'):
                question_index = key.replace('question_', '')
                answers[question_index] = value
        
        # Calculate score
        questions = quiz.questions
        import logging
        from difflib import SequenceMatcher

        logging.basicConfig(level=logging.DEBUG)

        total_questions = len(questions)
        correct_answers = 0

        def is_similar(a, b, threshold=0.8):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold

        start_time = time.time()
        for i, question in enumerate(questions):
            user_answer = answers.get(str(i), '').strip().lower()
            correct_answer = question.get('correct_answer', '').strip().lower()
    
            if question['type'] == 'multiple_choice':
                if user_answer == correct_answer:
                    correct_answers += 1
            elif question['type'] == 'true_false':
                if user_answer == correct_answer:
                    correct_answers += 1
            elif question['type'] == 'short_answer':
                    if is_similar(user_answer, correct_answer):
                        correct_answers += 1

        logging.debug(f"Scoring took {time.time() - start_time} seconds for {total_questions} questions")
        
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Save quiz attempt
        # Save quiz attempt
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            score=score
        )
        attempt.answers = answers

        db_start_time = time.time()
        db.session.add(attempt)
        db.session.commit()
        logging.debug(f"Database commit took {time.time() - db_start_time} seconds")

        flash(f'Quiz completed! Your score: {score:.1f}% ({correct_answers}/{total_questions})', 'success')
        return redirect(url_for('quiz_results', attempt_id=attempt.id))
        
        
    except Exception as e:
        logging.error(f"Error submitting quiz: {str(e)}")
        flash('An error occurred while submitting the quiz. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/quiz_results/<int:attempt_id>')
def quiz_results(attempt_id):
    """Display quiz results"""
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    return render_template('quiz_display.html', quiz=attempt.quiz, attempt=attempt, show_results=True)

@app.route('/quiz_history')
def quiz_history():
    """Display quiz history"""
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    attempts = QuizAttempt.query.order_by(QuizAttempt.completed_at.desc()).limit(20).all()
    return render_template('quiz_history.html', quizzes=quizzes, attempts=attempts)

@app.route('/export_quiz/<int:quiz_id>')
def export_quiz(quiz_id):
    """Export quiz as JSON"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    quiz_data = {
        'title': quiz.title,
        'course': quiz.course.title,
        'difficulty': quiz.difficulty,
        'created_at': quiz.created_at.isoformat(),
        'questions': quiz.questions
    }
    
    response = make_response(json.dumps(quiz_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=quiz_{quiz_id}.json'
    
    return response

@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    """Delete a course and all its quizzes"""
    try:
        course = Course.query.get_or_404(course_id)
        course_title = course.title
        
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Course "{course_title}" and all its quizzes have been deleted.', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logging.error(f"Error deleting course: {str(e)}")
        flash('An error occurred while deleting the course.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('index.html', error="An internal error occurred"), 500
