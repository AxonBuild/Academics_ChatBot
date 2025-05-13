import streamlit as st
import os
import asyncio
from dotenv import load_dotenv
import logging
from pathlib import Path
import pandas as pd

# Import the base query classifier
from base.query_classifier import classify_query_sync

# Import module-specific chatbots
from modules.course_information.chatbot import get_course_response_sync
from modules.class_schedules.chatbot import get_schedule_response_sync
from modules.exam_alerts.chatbot import get_exam_response_sync
from modules.study_resources.chatbot import get_resource_response_sync
from modules.professors.chatbot import get_professor_response_sync

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="University Assistant",
    page_icon="🎓",
    layout="wide"
)

# Define available models
AVAILABLE_MODELS = {
    "OpenAI GPT-4o Mini($0.15/M)": "gpt-4o-mini",
    "OpenAI GPT-4.1 Mini($0.40/M)": "gpt-4.1-mini",
    "OpenAI GPT-4.1-nano($0.10/M)": "gpt-4.1-nano",
    "Anthropic Claude 3 Haiku($0.25/M)": "openrouter/anthropic/claude-3-haiku",
    "Anthropic Claude 3 Sonnet($3/M)": "openrouter/anthropic/claude-3-sonnet",
    "Anthropic Claude 3 Opus($15/M)": "openrouter/anthropic/claude-3-opus",
    "Google Gemini 2.0 Flash($0.10/M)": "openrouter/google/gemini-2.0-flash-001",
}

# Module map
MODULES = {
    "course_information": {
        "name": "Course Information",
        "get_response": get_course_response_sync,
        "description": "Information about course content, prerequisites, credit hours, etc."
    },
    "class_schedules": {
        "name": "Class Schedules",
        "get_response": get_schedule_response_sync,
        "description": "Details about when and where classes meet"
    },
    "exam_alerts": {
        "name": "Exam Alerts",
        "get_response": get_exam_response_sync,
        "description": "Information about exam dates, deadlines, and assessments"
    },
    "study_resources": {
        "name": "Study Resources",
        "get_response": get_resource_response_sync,
        "description": "Materials for studying including textbooks and online resources"
    },
    "professors": {
        "name": "Professors",
        "get_response": get_professor_response_sync,
        "description": "Faculty information, office hours, and contact details"
    }
}

def get_module_response(query: str, language: str = "English") -> str:
    """
    Route the query to the appropriate module and get a response
    
    Args:
        query: The user's question
        language: The language for the response
        
    Returns:
        Formatted response string
    """
    try:
        # First, classify the query to determine which module should handle it
        classification = classify_query_sync(query)
        module_name = classification.module
        confidence = classification.confidence
        reasoning = classification.reasoning
        
        logger.info(f"Query classified as '{module_name}' with confidence {confidence}")
        
        # If low confidence, provide a notice about uncertainty
        prefix = ""
        if confidence < 0.5:
            if language.lower() == "arabic":
                prefix = "ملاحظة: لست متأكدًا تمامًا من نوع سؤالك، لكنني سأحاول الإجابة بأفضل ما لدي.\n\n"
            else:
                prefix = "Note: I'm not entirely sure about the category of your question, but I'll try my best to answer.\n\n"
        
        # Get the response function for the module
        if module_name in MODULES:
            response_func = MODULES[module_name]["get_response"]
            response = response_func(query, language)
            
            # Add debug info if in development
            debug_info = ""
            if os.getenv("APP_ENV") == "development":
                debug_info = f"\n\n---\nDebug: Query classified as '{module_name}' (confidence: {confidence:.2f})\nReasoning: {reasoning}"
            
            return prefix + response + debug_info
        else:
            # Fallback to general response if module not found
            if language.lower() == "arabic":
                return "عذرًا، لم أتمكن من فهم سؤالك. هل يمكنك إعادة صياغته أو تقديم مزيد من التفاصيل؟"
            else:
                return "I'm sorry, I couldn't understand your question. Could you rephrase it or provide more details?"
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        if language.lower() == "arabic":
            return "عذرًا، حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى لاحقًا."
        else:
            return "I'm sorry, an error occurred while processing your question. Please try again later."

# Main app
def main():
    st.title("🎓 University Assistant")
    
    # Sidebar with settings
    with st.sidebar:
        st.subheader("Settings")
        language = st.selectbox("Language / اللغة", ["English", "Arabic"])
        
        # Model selection dropdown - default to first model
        model_options = list(AVAILABLE_MODELS.keys())
        selected_model_name = st.selectbox(
            "Select AI Model",
            model_options,
            index=0
        )
        
        selected_model_id = AVAILABLE_MODELS[selected_model_name]
        
        # Store model ID in session state
        if "model" not in st.session_state or st.session_state.model != selected_model_id:
            st.session_state.model = selected_model_id
        
        # Clear conversation button
        if st.button("Clear Conversation"):
            if "messages" in st.session_state:
                st.session_state.messages = []
            st.rerun()
        
        # Show module information
        st.subheader("Available Modules")
        for module_id, module_info in MODULES.items():
            with st.expander(module_info["name"]):
                st.write(module_info["description"])
    
    st.subheader("University Information Assistant")
    st.write("Ask me anything about courses, schedules, exams, faculty, library resources, admission, or tuition!")
    
    # Display model being used
    st.caption(f"Currently using: {selected_model_name}")
    
    # Initialize chat history in session state if needed
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input for new message
    prompt = st.chat_input("Ask me a question...")
    
    if prompt:
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Add to session state message history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner(f"Thinking with {selected_model_name}..."):
                response = get_module_response(prompt, language=language)
                st.markdown(response)
        
        # Update message history
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()