import streamlit as st
import openai
import json
import requests
import base64
import re
import time
import random
from datetime import datetime
from syllabus import syllabus

# GitHub configuration
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
8. Make sure question must be IITJEE level 11th and 12th standard students will solve the problems.
9. Add some previous years IITJEE exam asked questions from 2010 to 2025.

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

def generate_test_id(teacher_name, date_str):
    """Generate test ID in format: teachername_YYYYMMDD_XX"""
    # Clean teacher name (remove spaces, convert to uppercase)
    clean_name = teacher_name.replace(" ", "").upper()
    # Generate random 2-digit number
    random_num = random.randint(10, 99)
    return f"{clean_name}_{date_str}_{random_num}"

def save_test_to_github(test_data, test_id, teacher_token):
    """Save test data to GitHub repository"""
    try:
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}/{test_id}.json"
        
        # Prepare the content
        content = json.dumps(test_data, indent=2)
        encoded_content = base64.b64encode(content.encode()).decode()
        
        # API request data
        data = {
            "message": f"Add test: {test_id}",
            "content": encoded_content,
            "branch": "main"  # or your default branch
        }
        
        # Headers
        headers = {
            "Authorization": f"token {teacher_token}",
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

def display_question_editor(question, question_num, key_prefix):
    """Display editable question interface"""
    st.markdown(f"### Question {question_num}")
    
    with st.container():
        # Question text editor
        question_text = st.text_area(
            "Question Text:",
            value=question.get('question_text', ''),
            key=f"{key_prefix}_question_{question_num}",
            height=100
        )
        
        # Options editor
        col1, col2 = st.columns(2)
        with col1:
            option_a = st.text_input(
                "Option A:",
                value=question.get('options', {}).get('A', ''),
                key=f"{key_prefix}_option_a_{question_num}"
            )
            option_b = st.text_input(
                "Option B:",
                value=question.get('options', {}).get('B', ''),
                key=f"{key_prefix}_option_b_{question_num}"
            )
        
        with col2:
            option_c = st.text_input(
                "Option C:",
                value=question.get('options', {}).get('C', ''),
                key=f"{key_prefix}_option_c_{question_num}"
            )
            option_d = st.text_input(
                "Option D:",
                value=question.get('options', {}).get('D', ''),
                key=f"{key_prefix}_option_d_{question_num}"
            )
        
        # Correct answer and metadata
        col3, col4, col5 = st.columns(3)
        with col3:
            correct_answer = st.selectbox(
                "Correct Answer:",
                options=['A', 'B', 'C', 'D'],
                index=['A', 'B', 'C', 'D'].index(question.get('correct_answer', 'A')),
                key=f"{key_prefix}_correct_{question_num}"
            )
        
        with col4:
            topic = st.text_input(
                "Topic:",
                value=question.get('topic', ''),
                key=f"{key_prefix}_topic_{question_num}"
            )
        
        with col5:
            difficulty = st.selectbox(
                "Difficulty:",
                options=['Easy', 'Medium', 'Hard'],
                index=['Easy', 'Medium', 'Hard'].index(question.get('difficulty', 'Medium')),
                key=f"{key_prefix}_difficulty_{question_num}"
            )
        
        # Explanation editor
        explanation = st.text_area(
            "Explanation:",
            value=question.get('explanation', ''),
            key=f"{key_prefix}_explanation_{question_num}",
            height=80
        )
        
        # Remove button
        remove_button = st.button(
            "🗑️ Remove Question",
            key=f"{key_prefix}_remove_{question_num}",
            type="secondary"
        )
        
        # Return updated question data
        updated_question = {
            "question_number": question_num,
            "question_text": question_text,
            "options": {
                "A": option_a,
                "B": option_b,
                "C": option_c,
                "D": option_d
            },
            "correct_answer": correct_answer,
            "explanation": explanation,
            "topic": topic,
            "subtopic": question.get('subtopic', ''),
            "difficulty": difficulty
        }
        
        return updated_question, remove_button

def display_new_question_form(question_num, key_prefix):
    """Display form for adding new question"""
    st.markdown(f"### Add New Question {question_num}")
    
    with st.container():
        # Question text
        question_text = st.text_area(
            "Question Text:",
            key=f"{key_prefix}_new_question_{question_num}",
            height=100
        )
        
        # Options
        col1, col2 = st.columns(2)
        with col1:
            option_a = st.text_input(
                "Option A:",
                key=f"{key_prefix}_new_option_a_{question_num}"
            )
            option_b = st.text_input(
                "Option B:",
                key=f"{key_prefix}_new_option_b_{question_num}"
            )
        
        with col2:
            option_c = st.text_input(
                "Option C:",
                key=f"{key_prefix}_new_option_c_{question_num}"
            )
            option_d = st.text_input(
                "Option D:",
                key=f"{key_prefix}_new_option_d_{question_num}"
            )
        
        # Correct answer and metadata
        col3, col4, col5 = st.columns(3)
        with col3:
            correct_answer = st.selectbox(
                "Correct Answer:",
                options=['A', 'B', 'C', 'D'],
                key=f"{key_prefix}_new_correct_{question_num}"
            )
        
        with col4:
            topic = st.text_input(
                "Topic:",
                key=f"{key_prefix}_new_topic_{question_num}"
            )
        
        with col5:
            difficulty = st.selectbox(
                "Difficulty:",
                options=['Easy', 'Medium', 'Hard'],
                key=f"{key_prefix}_new_difficulty_{question_num}"
            )
        
        # Explanation
        explanation = st.text_area(
            "Explanation:",
            key=f"{key_prefix}_new_explanation_{question_num}",
            height=80
        )
        
        # Add button
        add_button = st.button(
            "➕ Add This Question",
            key=f"{key_prefix}_add_{question_num}",
            type="primary"
        )
        
        # Return question data if valid
        if question_text and option_a and option_b and option_c and option_d and explanation:
            new_question = {
                "question_number": question_num,
                "question_text": question_text,
                "options": {
                    "A": option_a,
                    "B": option_b,
                    "C": option_c,
                    "D": option_d
                },
                "correct_answer": correct_answer,
                "explanation": explanation,
                "topic": topic,
                "subtopic": "",
                "difficulty": difficulty
            }
            return new_question, add_button
        
        return None, add_button

def main():
    st.set_page_config(
        page_title="Teacher MCQ Creator",
        page_icon="👨‍🏫",
        layout="wide"
    )
    
    st.title("👨‍🏫 Teacher MCQ Test Creator")
    st.markdown("Create and share MCQ tests with students using AI-powered question generation")
    
    # Initialize session state
    if 'questions_generated' not in st.session_state:
        st.session_state.questions_generated = False
    if 'mcq_questions' not in st.session_state:
        st.session_state.mcq_questions = []
    if 'test_published' not in st.session_state:
        st.session_state.test_published = False
    
    # Step 1: Initial Configuration
    if not st.session_state.questions_generated:
        st.header("🤖 AI Question Generation")
        st.markdown("Configure your test settings in the sidebar, then generate questions using AI.")
        
        # Sidebar for test inputs
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
        
        # Teacher Information
        st.sidebar.header("👨‍🏫 Teacher Information")
        teacher_name = st.sidebar.text_input(
            "Teacher Name*:",
            placeholder="Enter your full name",
            help="This will be used in the test ID and stored in the test file"
        )
        
        # API Configuration
        st.sidebar.header("🔑 API Configuration")
        
        # OpenAI API Key
        openai_api_key = st.sidebar.text_input(
            "OpenAI API Key:",
            type="password",
            help="Enter your OpenAI API key"
        )
        
        # Teacher Token (GitHub Token)
        teacher_token = st.sidebar.text_input(
            "Teacher Token:",
            type="password",
            help="Enter your GitHub Personal Access Token"
        )
        
        # Generate Questions Button
        if st.sidebar.button("🤖 Generate Questions", type="primary"):
            if not teacher_name:
                st.error("Please enter your teacher name")
                return
            
            if not openai_api_key:
                st.error("Please provide your OpenAI API key")
                return
            
            if not teacher_token:
                st.error("Please provide your Teacher Token")
                return
            
            if not selected_topics and not additional_info:
                st.error("Please select at least one topic or provide additional information")
                return
            
            # Store configuration in session state
            st.session_state.teacher_name = teacher_name
            st.session_state.selected_subject = selected_subject
            st.session_state.selected_topics = selected_topics
            st.session_state.additional_info = additional_info
            st.session_state.num_questions = num_questions
            st.session_state.difficulty_level = difficulty_level
            st.session_state.teacher_token = teacher_token
            
            # Show loading spinner
            with st.spinner("Generating questions... This may take a few moments."):
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
                    
                    if mcq_data and 'questions' in mcq_data:
                        st.session_state.mcq_questions = mcq_data['questions']
                        st.session_state.questions_generated = True
                        st.success("✅ Questions generated successfully! You can now edit, remove, or add questions.")
                        st.rerun()
                    else:
                        st.error("Failed to parse generated questions. Please try again.")
                else:
                    st.error("Failed to generate questions. Please check your API key and try again.")
    
    # Step 2: Question Management
    elif st.session_state.questions_generated and not st.session_state.test_published:
        st.header("📝 Question Management")
        st.markdown(f"**Teacher:** {st.session_state.teacher_name}")
        st.markdown(f"**Subject:** {st.session_state.selected_subject}")
        st.markdown(f"**Topics:** {', '.join(st.session_state.selected_topics)}")
        
        # Question editing interface
        questions_to_remove = []
        updated_questions = []
        
        # Edit existing questions
        for i, question in enumerate(st.session_state.mcq_questions):
            st.markdown("---")
            updated_question, remove_clicked = display_question_editor(
                question, i + 1, "edit"
            )
            
            if remove_clicked:
                questions_to_remove.append(i)
            else:
                updated_questions.append(updated_question)
        
        # Remove questions if requested
        if questions_to_remove:
            for index in sorted(questions_to_remove, reverse=True):
                st.session_state.mcq_questions.pop(index)
            st.rerun()
        
        # Update question numbers
        for i, question in enumerate(updated_questions):
            question['question_number'] = i + 1
        
        st.session_state.mcq_questions = updated_questions
        
        # Add new question section
        st.markdown("---")
        st.header("➕ Add New Question")
        
        new_question_num = len(st.session_state.mcq_questions) + 1
        new_question, add_clicked = display_new_question_form(new_question_num, "new")
        
        if add_clicked and new_question:
            st.session_state.mcq_questions.append(new_question)
            st.success("✅ Question added successfully!")
            st.rerun()
        elif add_clicked:
            st.error("Please fill in all required fields to add the question.")
        
        # Publish Test Section
        st.markdown("---")
        st.header("🚀 Publish Test")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Questions", len(st.session_state.mcq_questions))
        with col2:
            st.metric("Subject", st.session_state.selected_subject)
        with col3:
            st.metric("Difficulty", st.session_state.difficulty_level)
        
        if st.button("📤 Publish Test", type="primary"):
            if len(st.session_state.mcq_questions) == 0:
                st.error("Cannot publish test with no questions!")
                return
            
            # Generate test ID
            date_str = datetime.now().strftime("%Y%m%d")
            test_id = generate_test_id(st.session_state.teacher_name, date_str)
            
            # Create test data with teacher name first
            test_data = {
                "teacher_name": st.session_state.teacher_name,
                "test_id": test_id,
                "created_at": datetime.now().isoformat(),
                "subject": st.session_state.selected_subject,
                "topics": st.session_state.selected_topics,
                "additional_info": st.session_state.additional_info,
                "difficulty": st.session_state.difficulty_level,
                "total_questions": len(st.session_state.mcq_questions),
                "questions": st.session_state.mcq_questions
            }
            
            # Save to GitHub
            with st.spinner("Publishing test to GitHub..."):
                success, message = save_test_to_github(test_data, test_id, st.session_state.teacher_token)
                
                if success:
                    st.session_state.test_published = True
                    st.session_state.published_test_id = test_id
                    st.success(f"✅ Test published successfully!")
                    st.success(f"📋 **Test ID:** `{test_id}`")
                    st.info("Share this Test ID with your students to take the test")
                    st.balloons()
                else:
                    st.error(f"❌ Failed to publish test: {message}")
    
    # Step 3: Test Published
    elif st.session_state.test_published:
        st.header("🎉 Test Published Successfully!")
        
        st.success(f"📋 **Test ID:** `{st.session_state.published_test_id}`")
        st.info("Share this Test ID with your students")
        
        # Display test summary
        st.markdown("### 📊 Test Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Teacher:** {st.session_state.teacher_name}")
            st.info(f"**Subject:** {st.session_state.selected_subject}")
            st.info(f"**Topics:** {', '.join(st.session_state.selected_topics)}")
        with col2:
            st.info(f"**Total Questions:** {len(st.session_state.mcq_questions)}")
            st.info(f"**Difficulty:** {st.session_state.difficulty_level}")
            st.info(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Reset button
        if st.button("🔄 Create Another Test", type="primary"):
            # Clear session state
            st.session_state.questions_generated = False
            st.session_state.mcq_questions = []
            st.session_state.test_published = False
            if 'published_test_id' in st.session_state:
                del st.session_state.published_test_id
            st.rerun()
    
    # Information section
    with st.expander("ℹ️ How to use this application"):
        st.markdown("""
        ### Teacher Workflow:
        1. **Configure Test**: Enter your name, select subject, topics, and difficulty level
        2. **Generate Questions**: AI will create questions based on your configuration
        3. **Edit Questions**: Review, edit, remove, or add questions as needed
        4. **Publish Test**: Create final test and get Test ID for students
        
        ### Features:
        - ✅ AI-powered question generation
        - ✅ Full question editing capabilities
        - ✅ Add/remove questions manually
        - ✅ Test ID format: `TEACHERNAME_YYYYMMDD_XX`
        - ✅ Automatic GitHub storage
        - ✅ Student-friendly test sharing
        
        ### Important Notes:
        - Teacher name is required and will be part of the Test ID
        - All questions can be edited after AI generation
        - Test ID format: Teacher name + Date + Random number
        - Share the Test ID with students to take the test
        """)

if __name__ == "__main__":
    main() 
