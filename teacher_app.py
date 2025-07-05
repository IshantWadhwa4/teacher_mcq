import streamlit as st
import openai
from syllabus import syllabus
import json
import re
import time
import os
import requests
import base64
from datetime import datetime

# GitHub configuration
GITHUB_TOKEN = "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"  # Replace with your new token
GITHUB_REPO = "IshantWadhwa4/data_tsmcq"
GITHUB_PATH = "questions"  # Path where test files will be stored

def get_topics_for_subject(subject):
    """Get topics for a given subject from syllabus"""
    if subject in syllabus:
        return list(syllabus[subject].keys())
    return []

def create_openai_prompt(subject, topics, additional_info, num_questions, level, syllabus_data):
    """Create a detailed prompt for OpenAI to generate MCQs"""
    
    # Get syllabus information for selected topics
    topic_descriptions = ""
    for topic in topics:
        if topic in syllabus_data[subject]:
            topic_descriptions += f"\n- {topic}: {syllabus_data[subject][topic]['description']}"
            topic_descriptions += f"\n  Past Questions Pattern: {syllabus_data[subject][topic]['past_questions']}"
    
    prompt = f"""
Generate {num_questions} multiple-choice questions (MCQs) for {subject} examination.

SUBJECT: {subject}

TOPICS TO COVER:
{topic_descriptions}

ADDITIONAL REQUIREMENTS:
{additional_info if additional_info else "None"}

DIFFICULTY LEVEL: {level}
- If Easy: Focus on direct application of formulas and basic concepts
- If Medium: Require 2-3 step problem solving and concept understanding
- If Hard: Complex multi-step problems requiring deep understanding and multiple concept integration
- If Mix: Include a mixture of easy, medium, and hard questions

INSTRUCTIONS:
1. Generate exactly {num_questions} questions
2. Each question should have exactly 4 options (A, B, C, D)
3. Only one option should be correct
4. Questions should be educational and test understanding
5. Include numerical problems, conceptual questions, and application-based questions
6. Ensure questions are unambiguous and have clear correct answers
7. Provide detailed explanations for correct answers

FORMAT YOUR RESPONSE AS JSON:
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Question text here",
      "options": {{
        "A": "Option A text",
        "B": "Option B text", 
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Detailed explanation of why this answer is correct",
      "topic": "Specific topic from the syllabus",
      "subtopic": "Specific subtopic if applicable",
      "difficulty": "Easy/Medium/Hard"
    }}
  ]
}}

Make sure the JSON is properly formatted and can be parsed.
"""
    return prompt

def generate_mcqs(api_key, prompt):
    """Generate MCQs using OpenAI API"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert examination question creator. Generate high-quality multiple-choice questions following the exact format requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

def parse_mcq_response(response_text):
    """Parse the OpenAI response to extract MCQ data"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            mcq_data = json.loads(json_text)
            return mcq_data
        else:
            st.error("Could not find valid JSON in the response")
            return None
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON response: {str(e)}")
        return None

def save_test_to_github(test_data, exam_token):
    """Save test data to GitHub repository"""
    try:
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}/{exam_token}.json"
        
        # Prepare the content
        content = json.dumps(test_data, indent=2)
        encoded_content = base64.b64encode(content.encode()).decode()
        
        # API request data
        data = {
            "message": f"Add test: {exam_token}",
            "content": encoded_content,
            "branch": "main"  # or your default branch
        }
        
        # Headers
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Make the request
        response = requests.put(url, json=data, headers=headers)
        
        if response.status_code == 201:
            return True, "Test successfully saved to GitHub"
        else:
            return False, f"Error saving to GitHub: {response.status_code} - {response.text}"
    
    except Exception as e:
        return False, f"Error saving test to GitHub: {str(e)}"

def display_mcqs_preview(mcq_data):
    """Display MCQs in preview format"""
    if not mcq_data or 'questions' not in mcq_data:
        st.error("No valid question data to display")
        return
    
    for i, question in enumerate(mcq_data['questions'], 1):
        with st.expander(f"Question {i}: {question['question_text'][:50]}..."):
            st.write(f"**Question:** {question['question_text']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Options:**")
                for option_key, option_text in question['options'].items():
                    if option_key == question['correct_answer']:
                        st.write(f"✅ **{option_key}.** {option_text}")
                    else:
                        st.write(f"   **{option_key}.** {option_text}")
            
            with col2:
                st.write(f"**Correct Answer:** {question['correct_answer']}")
                st.write(f"**Topic:** {question.get('topic', 'General')}")
                st.write(f"**Subtopic:** {question.get('subtopic', 'N/A')}")
                st.write(f"**Difficulty:** {question.get('difficulty', 'Medium')}")
            
            st.write(f"**Explanation:** {question.get('explanation', 'No explanation provided')}")

def main():
    st.set_page_config(
        page_title="Teacher MCQ Creator",
        page_icon="👨‍🏫",
        layout="wide"
    )
    
    st.title("👨‍🏫 Teacher MCQ Test Creator")
    st.markdown("Create and share MCQ tests with students using AI-powered question generation")
    
    # Sidebar for inputs
    st.sidebar.header("📝 Test Configuration")
    
    # Subject selection
    subjects = ["Mathematics", "Physics", "Chemistry", "Biology"]
    selected_subject = st.sidebar.selectbox(
        "Select Subject:",
        subjects,
        help="Choose the subject for the test"
    )
    
    # Topics selection
    available_topics = get_topics_for_subject(selected_subject)
    if available_topics:
        selected_topics = st.sidebar.multiselect(
            "Select Topics:",
            available_topics,
            help="Choose specific topics from the syllabus"
        )
    else:
        st.sidebar.warning(f"No topics found for {selected_subject}. Please add topics in additional information.")
        selected_topics = []
    
    # Additional information
    additional_info = st.sidebar.text_area(
        "Additional Topic Information (Optional):",
        placeholder="Enter any specific requirements, topics to focus on, or additional context...",
        help="Provide additional context for question generation"
    )
    
    # Number of questions
    num_questions = st.sidebar.slider(
        "Number of Questions:",
        min_value=5,
        max_value=50,
        value=10,
        help="Select number of questions (5-50)"
    )
    
    # Difficulty level
    difficulty_level = st.sidebar.selectbox(
        "Difficulty Level:",
        ["Easy", "Medium", "Hard", "Mix"],
        index=3,
        help="Choose the difficulty level for the test"
    )
    
    # API Configuration
    st.sidebar.header("🔑 API Configuration")
    
    # OpenAI API Key
    openai_api_key = st.sidebar.text_input(
        "OpenAI API Key:",
        type="password",
        help="Enter your OpenAI API key"
    )
    
    # GitHub Configuration (Display only)
    st.sidebar.markdown("### 📂 GitHub Configuration")
    st.sidebar.info(f"Repository: {GITHUB_REPO}")
    st.sidebar.info(f"Path: {GITHUB_PATH}")
    
    # Generate Test
    if st.sidebar.button("🚀 Generate Test", type="primary"):
        if not openai_api_key:
            st.error("Please provide your OpenAI API key")
            return
        
        if not selected_topics and not additional_info:
            st.error("Please select at least one topic or provide additional information")
            return
        
        # Generate exam token
        exam_token = f"test_{int(time.time())}"
        
        # Show loading spinner
        with st.spinner("Generating test questions... This may take a few moments."):
            # Create prompt
            prompt = create_openai_prompt(
                selected_subject, 
                selected_topics, 
                additional_info, 
                num_questions, 
                difficulty_level, 
                syllabus
            )
            
            # Generate MCQs
            response = generate_mcqs(openai_api_key, prompt)
            
            if response:
                # Parse response
                mcq_data = parse_mcq_response(response)
                
                if mcq_data:
                    # Create test data with metadata
                    test_data = {
                        "exam_token": exam_token,
                        "created_at": datetime.now().isoformat(),
                        "created_by": "Teacher",
                        "subject": selected_subject,
                        "topics": selected_topics,
                        "additional_info": additional_info,
                        "difficulty": difficulty_level,
                        "num_questions": num_questions,
                        "questions": mcq_data['questions']
                    }
                    
                    # Save to GitHub
                    success, message = save_test_to_github(test_data, exam_token)
                    
                    if success:
                        st.success(f"✅ Test successfully created and saved!")
                        st.success(f"📋 **Exam Token:** `{exam_token}`")
                        st.info("Share this exam token with your students to take the test")
                        
                        # Display preview
                        st.header("📋 Test Preview")
                        display_mcqs_preview(mcq_data)
                        
                        # Download option
                        st.sidebar.markdown("---")
                        st.sidebar.download_button(
                            label="📥 Download Test (JSON)",
                            data=json.dumps(test_data, indent=2),
                            file_name=f"{exam_token}.json",
                            mime="application/json"
                        )
                        
                        # Copy exam token
                        st.sidebar.markdown("### 🔗 Share with Students")
                        st.sidebar.code(exam_token, language=None)
                        st.sidebar.markdown("*Copy the exam token above to share with students*")
                        
                    else:
                        st.error(f"❌ Failed to save test: {message}")
    
    # Information section
    with st.expander("ℹ️ How to use this app"):
        st.markdown("""
        ### Steps to create a test:
        1. **Select Subject**: Choose from Mathematics, Physics, Chemistry, or Biology
        2. **Choose Topics**: Select specific topics from the syllabus
        3. **Add Details**: Optionally provide additional requirements or focus areas
        4. **Set Parameters**: Choose number of questions (5-50) and difficulty level
        5. **API Key**: Enter your OpenAI API key
        6. **Generate**: Click generate and share the exam token with students
        
        ### GitHub Integration:
        - Tests are automatically saved to the configured GitHub repository
        - No additional setup required from teachers
        
        ### Features:
        - ✅ AI-powered question generation
        - ✅ Multiple difficulty levels including Mix
        - ✅ Detailed explanations for each answer
        - ✅ Automatic saving to GitHub
        - ✅ Shareable exam tokens
        - ✅ Topic-based question generation
        """)

if __name__ == "__main__":
    main() 
