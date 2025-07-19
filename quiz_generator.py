import os
import logging
import random
from groq import Groq
import json
import re
from dotenv import load_dotenv


class QuizGenerator:
    def __init__(self):
        """Initialize the QuizGenerator with Groq client"""
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logging.error("GROQ_API_KEY not found in environment variables")
            self.client = None
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                logging.info("Groq client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Groq client: {str(e)}")
                self.client = None
    
    def generate_quiz(self, content, num_questions=5, difficulty='medium', question_types=None):
        """
        Generate a quiz from the given content using Groq API
        
        Args:
            content (str): Course content to generate quiz from
            num_questions (int): Number of questions to generate
            difficulty (str): Difficulty level (easy, medium, hard)
            question_types (list): Types of questions to include
            
        Returns:
            list: List of question dictionaries
        """
        if not self.client:
            logging.error("Groq client not initialized")
            return []
        
        if not question_types:
            question_types = ['multiple_choice', 'true_false', 'short_answer']
        
        try:
            logging.info(f"Starting quiz generation: {num_questions} questions, difficulty: {difficulty}")
            
            # Create a diverse set of questions by using different prompts and techniques
            questions = []
            
            # Split content into meaningful chunks
            content_chunks = self._split_content(content, num_questions)
            if not content_chunks:
                logging.error("No content chunks available")
                return []
            
            # Generate questions more efficiently
            for i in range(min(num_questions, len(content_chunks) * 2)):  # Limit attempts
                question_type = random.choice(question_types)
                chunk = content_chunks[i % len(content_chunks)]
                
                # Skip very short chunks
                if len(chunk.strip()) < 20:
                    continue
                
                # Add randomization elements to ensure variety
                variation_seed = random.randint(1, 1000)
                focus_aspect = random.choice(['concepts', 'details', 'applications', 'examples', 'relationships'])
                
                question = self._generate_single_question(
                    chunk, question_type, difficulty, variation_seed, focus_aspect
                )
                
                if question and not self._is_duplicate_question(question, questions):
                    questions.append(question)
                    logging.info(f"Generated question {len(questions)}/{num_questions}")
                    
                    # Stop if we have enough questions
                    if len(questions) >= num_questions:
                        break
            
            logging.info(f"Quiz generation completed: {len(questions)} questions generated")
            return questions[:num_questions]
            
        except Exception as e:
            logging.error(f"Error generating quiz: {str(e)}")
            return []
    
    def _split_content(self, content, num_questions):
        """Split content into chunks for varied question generation"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < num_questions:
            return [content]  # Return full content if not enough sentences
        
        chunk_size = max(2, len(sentences) // num_questions)
        chunks = []
        
        for i in range(0, len(sentences), chunk_size):
            chunk = '. '.join(sentences[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks if chunks else [content]
    
    def _generate_single_question(self, content, question_type, difficulty, variation_seed, focus_aspect):
        """Generate a single question using Groq API"""
        try:
            prompt = self._create_prompt(content, question_type, difficulty, variation_seed, focus_aspect)
            
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert quiz generator. Create diverse, educational questions based on the provided content. Always respond with valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama3-8b-8192",  # Using Llama3 model on Groq
                temperature=0.7,  # Balanced temperature for quality and speed
                max_tokens=500,  # Reduced for faster responses
                top_p=0.8
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                question_data = json.loads(json_match.group())
                question_data['type'] = question_type
                return question_data
            else:
                logging.error(f"No valid JSON found in response: {response_text}")
                return None
                
        except Exception as e:
            logging.error(f"Error generating single question: {str(e)}")
            return None
    
    def _create_prompt(self, content, question_type, difficulty, variation_seed, focus_aspect):
        """Create a prompt for question generation"""
        base_prompt = f"""
        Based on the following content, create a {difficulty} difficulty {question_type.replace('_', ' ')} question.
        
        Focus on: {focus_aspect}
        Variation seed: {variation_seed} (use this to ensure variety in your approach)
        
        Content:
        {content}
        
        Requirements:
        - Make the question educational and relevant to the content
        - Ensure the question tests understanding, not just memorization
        - Use the variation seed to create a unique perspective or angle
        """
        
        if question_type == 'multiple_choice':
            prompt = base_prompt + """
            
            Return a JSON object with this exact structure:
            {
                "question": "Your question here",
                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                "correct_answer": "a",
                "explanation": "Brief explanation of why this answer is correct"
            }
            
            Make sure one option is clearly correct and others are plausible but wrong.
            The correct_answer should be "a", "b", "c", or "d" (lowercase).
            """
        
        elif question_type == 'true_false':
            prompt = base_prompt + """
            
            Return a JSON object with this exact structure:
            {
                "question": "Your true/false statement here",
                "correct_answer": "true",
                "explanation": "Brief explanation of why this answer is correct"
            }
            
            The correct_answer should be either "true" or "false" (lowercase).
            Make the statement clear and unambiguous.
            """
        
        elif question_type == 'short_answer':
            prompt = base_prompt + """
            
            Return a JSON object with this exact structure:
            {
                "question": "Your question here",
                "correct_answer": "Expected answer",
                "explanation": "Brief explanation and acceptable variations of the answer"
            }
            
            Keep the expected answer concise (1-3 words when possible).
            The question should have a clear, specific answer.
            """
        
        return prompt
    
    def _is_duplicate_question(self, new_question, existing_questions):
        """Check if a question is similar to existing ones"""
        if not existing_questions:
            return False
        
        new_q_text = new_question.get('question', '').lower()
        
        for existing in existing_questions:
            existing_q_text = existing.get('question', '').lower()
            
            # Simple similarity check - count common words
            new_words = set(new_q_text.split())
            existing_words = set(existing_q_text.split())
            
            if len(new_words & existing_words) / max(len(new_words), len(existing_words)) > 0.6:
                return True
        
        return False
