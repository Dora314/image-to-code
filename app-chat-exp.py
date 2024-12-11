import streamlit as st
import pathlib
from PIL import Image
import google.generativeai as genai
import tempfile
import markdown  # For rendering HTML
from dotenv import load_dotenv
import os

# Configure the API key directly in the script (replace with your actual key)
API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=API_KEY)

# Generation configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Safety settings
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Model name
MODEL_NAME = "gemini-2.0-flash-exp"

# Framework selection (e.g., Tailwind, Bootstrap, etc.)
framework = "Regular CSS"  # Change as needed

# Create the model
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    safety_settings=safety_settings,
    generation_config=generation_config,
)

# Start a chat session
chat_session = model.start_chat(history=[])

# Function to send a message to the model
def send_message_to_model(message, image_path=None):
    if image_path:
        image_input = {
            'mime_type': 'image/jpeg',
            'data': pathlib.Path(image_path).read_bytes()
        }
        response = chat_session.send_message([message, image_input])
    else:
        response = chat_session.send_message(message)
    return response.text

# Streamlit app
def main():
    st.title("UI to HTML with Gemini")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        try:
            # Load and display the image
            image = Image.open(uploaded_file)
            st.image(image, caption='Uploaded Image.', use_container_width=True)

            # Convert image to RGB if it has an alpha channel
            if image.mode == 'RGBA':
                image = image.convert('RGB')

            # Save the uploaded image temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_image:
                image.save(temp_image, format="JPEG")
                temp_image_path = temp_image.name

            # Initialize session state variables if they don't exist
            if 'refined_html' not in st.session_state:
                st.session_state['refined_html'] = ""
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []

            # Generate UI description
            if st.button("Code UI"):
                with st.spinner("🧑‍💻 Looking at your UI..."):
                    prompt = "Describe this UI in accurate details. When you reference a UI element put its name and bounding box in the format: [object name (y_min, x_min, y_max, x_max)]. Also Describe the color of the elements."
                    description = send_message_to_model(prompt, temp_image_path)
                    st.write(description)

                with st.spinner("🔍 Refining description with visual comparison..."):
                    refine_prompt = f"Compare the described UI elements with the provided image and identify any missing elements or inaccuracies. Also Describe the color of the elements. Provide a refined and accurate description of the UI elements based on this comparison. Here is the initial description: {description}"
                    refined_description = send_message_to_model(refine_prompt, temp_image_path)
                    st.write(refined_description)

                with st.spinner("🛠️ Generating website..."):
                    html_prompt = f"Create an HTML file based on the following UI description, using the UI elements described in the previous response. Include {framework} CSS within the HTML file to style the elements. Make sure the colors used are the same as the original UI. The UI needs to be responsive and mobile-first, matching the original UI as closely as possible. Do not include any explanations or comments. Avoid using ```html. and ``` at the end. ONLY return the HTML code with inline CSS. Here is the refined description: {refined_description}"
                    initial_html = send_message_to_model(html_prompt, temp_image_path)

                with st.spinner("🔧 Refining website..."):
                    refine_html_prompt = f"Validate the following HTML code based on the UI description and image and provide a refined version of the HTML code with {framework} CSS that improves accuracy, responsiveness, and adherence to the original design. ONLY return the refined HTML code with inline CSS. Avoid using ```html. and ``` at the end. Here is the initial HTML: {initial_html}"
                    st.session_state['refined_html'] = send_message_to_model(refine_html_prompt, temp_image_path)
                    st.session_state['chat_history'].append(("Initial HTML Code", st.session_state['refined_html']))

            # Display chat history
            for role, text in st.session_state['chat_history']:
                with st.chat_message(role):
                  st.markdown(text)

            # Chat input for further refinement
            user_input = st.chat_input("Ask a question or request a change")
            if user_input:
                st.session_state['chat_history'].append(("user", user_input))
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.spinner("🤖 Thinking..."):
                    # Include previous HTML for context
                    refine_html_prompt = f"Here is the current HTML code:\n```html\n{st.session_state['refined_html']}\n```\n\nUser request: {user_input}\n\nBased on this request, generate the updated HTML code. Remember to ONLY return the refined HTML code with inline {framework} CSS. Avoid using ```html. and ``` at the end."
                    updated_html = send_message_to_model(refine_html_prompt)
                    st.session_state['refined_html'] = updated_html
                    st.session_state['chat_history'].append(("assistant", updated_html))
                    with st.chat_message("assistant"):
                        st.markdown(updated_html)

            # Display the refined HTML if available
            if st.session_state['refined_html']:
                st.code(st.session_state['refined_html'], language='html')

                # Preview the HTML with dynamic width
                html_with_js = f"""
                    <div id="preview-container">
                        {st.session_state['refined_html']}
                    </div>
                    <script>
                        const container = document.getElementById('preview-container');
                        function resizeIframe() {{
                            container.style.width = window.innerWidth + 'px';
                        }}
                        resizeIframe();
                        window.addEventListener('resize', resizeIframe);
                    </script>
                """

                st.write("Preview:")
                st.components.v1.html(html_with_js, height=600, scrolling=True)

                # Provide download link for HTML
                st.download_button(label="Download HTML", data=st.session_state['refined_html'], file_name="index.html", mime="text/html")

        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()