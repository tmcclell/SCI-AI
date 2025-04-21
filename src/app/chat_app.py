import streamlit as st
from dotenv import load_dotenv
import uuid
import requests
import time
import re
import streamlit.components.v1 as components
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
import PyPDF2

# Load environment variables
load_dotenv(override=True)

# Endpoints from environment variables
AGENT_ENDPOINT = 'http://127.0.0.1:8005'
AZURE_COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT")
AZURE_COMPUTER_VISION_KEY = os.getenv("AZURE_COMPUTER_VISION_KEY")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

################################################################################
#                                   MAIN
################################################################################

st.set_page_config(
    page_title="Sustainable Azure AI Agent Demo",
    layout="wide",  # wide mode
)
st.title("Azure AI Agent Demos")

st.subheader("Sustainable AI Agent")
st.text('Solution to help developers understand the impact of their code on the environment.')

# Initialize MathJax with auto-rendering and better configuration
def init_mathjax():
    return components.html(
        """
        <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']],
                processEscapes: true,
                processEnvironments: true
            },
            svg: {
                fontCache: 'global'
            },
            options: {
                enableMenu: false,
                renderActions: {
                    addMenu: [],
                    checkLoading: []
                }
            },
            startup: {
                typeset: true,
                pageReady: function() {
                    return MathJax.startup.defaultPageReady().then(function() {
                        console.log('MathJax initial typesetting complete');
                    });
                }
            }
        };
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
        """,
        height=0,
    )

# Helper function to process LaTeX equations
def process_latex(text):
    if not text:
        return text
        
    # First, protect existing properly formatted LaTeX
    protected_blocks = {}
    protected_count = 0
    
    # Protect existing display math blocks
    for match in re.finditer(r'\$\$(.*?)\$\$', text, re.DOTALL):
        placeholder = f"__PROTECTED_DISPLAY_MATH_{protected_count}__"
        protected_blocks[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder)
        protected_count += 1
    
    # Protect existing inline math blocks
    for match in re.finditer(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', text, re.DOTALL):
        placeholder = f"__PROTECTED_INLINE_MATH_{protected_count}__"
        protected_blocks[placeholder] = match.group(0)
        text = text.replace(match.group(0), placeholder)
        protected_count += 1
    
    # Process equations with LaTeX syntax but not enclosed in LaTeX delimiters
    patterns = [
        # Detect common equation patterns without delimiters
        (r'(?<![\\$])([a-zA-Z0-9_]+\s*=\s*[a-zA-Z0-9_\^\/\*\+\-\(\)\.]+)', r'$\1$'),
        # Detect LaTeX commands without delimiters
        (r'(?<![\\$])(\\[a-zA-Z]+\{.*?\})', r'$\1$'),
        # More specific LaTeX command patterns
        (r'(?<![\\$])(\\sum|\\prod|\\int|\\frac)(\{.*?\}\{.*?\})', r'$\1\2$'),
        # Pattern for expressions like \text{...}
        (r'(?<![\\$])(\\text\{.*?\})', r'$\1$')
    ]
    
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    
    # Ensure proper spacing for LaTeX delimiters
    text = re.sub(r'(?<!\$)\$(?!\$)', ' $ ', text)
    text = re.sub(r'\$\$', ' $$ ', text)
    
    # Replace common LaTeX environments
    text = text.replace('\\begin{equation}', '$$')
    text = text.replace('\\end{equation}', '$$')
    
    # Clean up potential issues
    text = re.sub(r'\$\s*\$', '$', text)  # Empty math delimiters
    text = re.sub(r'\$\$\s*\$\$', '$$', text)  # Empty display math delimiters
    
    # Restore protected blocks
    for placeholder, original in protected_blocks.items():
        text = text.replace(placeholder, original)
    
    return text

# Function to force MathJax typesetting
def force_mathjax_typeset():
    return components.html(
        """
        <script>
        if (typeof window.MathJax !== 'undefined') {
            try {
                MathJax.typesetPromise().catch(err => console.error('MathJax typesetting failed:', err));
            } catch (e) {
                console.error('Error during MathJax typesetting:', e);
            }
        } else {
            console.warn('MathJax not loaded yet');
        </script>
        """,
        height=0,
    )

# Function to extract text from images using Azure AI Vision Image Analysis
# Reference: https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/quickstarts-sdk/image-analysis-client-library?tabs=python

def extract_text_from_image(image_file):
    try:
        client = ImageAnalysisClient(
            endpoint=AZURE_COMPUTER_VISION_ENDPOINT,
            credential=AzureKeyCredential(AZURE_COMPUTER_VISION_KEY)
        )
        image_bytes = image_file.read()
        result = client.analyze(
            image_data=image_bytes,
            visual_features=["read"]
        )
        if result.read and result.read.blocks:
            text = " ".join([line.text for block in result.read.blocks for line in block.lines])
            return text
        else:
            return None
    except Exception as e:
        st.error(f"Error extracting text from image: {str(e)}")
        return None

# Function to extract text from PDF using PyPDF2
def extract_text_from_pdf(pdf_file):
    try:
        pdf_file.seek(0)
        reader = PyPDF2.PdfReader(pdf_file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip() if text else None
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None

# Call MathJax initialization
init_mathjax()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(process_latex(message["content"]), unsafe_allow_html=True)

# Force typeset after displaying all messages
force_mathjax_typeset()

# File upload section
uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

user_input = None  # Ensure user_input is always defined

if uploaded_file:
    file_type = uploaded_file.type
    if file_type == "application/pdf":
        extracted_text = extract_text_from_pdf(uploaded_file)
        if extracted_text:
            st.write("Extracted Text from PDF:", extracted_text[:1000] + ("..." if len(extracted_text) > 1000 else ""))
            user_input = f"Analyze this extracted text from PDF: {extracted_text}"
        else:
            st.error("No text could be extracted from the PDF.")
    elif file_type in ["image/png", "image/jpeg"]:
        extracted_text = extract_text_from_image(uploaded_file)
        if extracted_text:
            st.write("Extracted Text from Image:", extracted_text)
            user_input = f"Analyze this extracted text from image: {extracted_text}"
        else:
            st.error("No text could be extracted from the image.")
    else:
        st.error("Unsupported file type. Please upload a PDF or an image.")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        # Create a placeholder for the assistant's response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                # Show a status while processing
                message_placeholder.markdown("Processing your request...", unsafe_allow_html=True)

                # Stream the response
                with requests.post(
                    f"{AGENT_ENDPOINT}/chat",
                    json={"messages": [user_input]},
                    stream=True
                ) as response:
                    response.raise_for_status()

                    # Use an iterator for the response content
                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                        if chunk:
                            full_response += chunk
                            # Format with MathJax support
                            formatted_response = process_latex(full_response)
                            message_placeholder.markdown(formatted_response + "▌", unsafe_allow_html=True)

                            # Force MathJax typesetting each time content is updated
                            force_mathjax_typeset()
                            time.sleep(0.01)  # Small delay for smoother appearance

                    # Final update without the cursor
                    formatted_response = process_latex(full_response)
                    message_placeholder.markdown(formatted_response, unsafe_allow_html=True)

                    # Final typesetting to ensure all math is rendered
                    force_mathjax_typeset()

            except Exception as e:
                st.error(f"Error communicating with the agent: {str(e)}")
                full_response = f"Error: {str(e)}"
                message_placeholder.markdown(full_response)

            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

# Chat input
TASK = "calculate the Software Carbon Intensity (SCI) for a software application."
USER_INPUTS = [
    "calculate the Software Carbon Intensity (SCI) of this software solution."
    "1. Neo4j API: Azure App Service, Memory Allocation: 1.75G, Memory Utilization: 70%, CPU Allocated: 1 vCPU, CPU Utilization: 25%, Compute: APIs are S1:1 app services" 
    "2. Graph DB: Neo4J:Memory Allocation 32G, Memory Utilization: 6.3G, CPU Allocated: 8 vCPU, CPU Utilization: 28%, Compute: D8ds VMs (8 vcpus, 32 GiB memory)"
    "3. TigerGraph API: Azure App Service, Memory Allocation: 1.75G, Memory Utilization: 70%, CPU Allocated: 1 vCPU, CPU Utilization: 25%, Compute: APIs are S1:1 app services"
    "4. Graph DB TigerGraph: Memory Allocation: 32G, Memory Utilization: 6%, CPU Allocated: 8 vCPU, CPU Utilization: 17%, Compute: D8ds VMs (8 vcpus, 32 GiB memory)"
    "Country workload resides: USA "
    "Assume R is per hour. "
]

# Create columns for example task button and custom chat
col1, col2 = st.columns([1, 3])

with col1:
    example_clicked = st.button("Send Example SCI Task")
    
# New chat input field
chat_input = st.chat_input("Type your message here...")

# Process input from either source
user_input = None

if example_clicked:
    user_input = "\n".join(USER_INPUTS)
    st.session_state.input_source = "example"
elif chat_input:
    user_input = chat_input
    st.session_state.input_source = "chat"

if user_input:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Create a placeholder for the assistant's response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Show a status while processing
            message_placeholder.markdown("Processing your request...", unsafe_allow_html=True)
            
            # Stream the response
            with requests.post(
                f"{AGENT_ENDPOINT}/chat",
                json={"messages": [user_input]},
                stream=True
            ) as response:
                response.raise_for_status()
                
                # Use an iterator for the response content
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        full_response += chunk
                        # Format with MathJax support
                        formatted_response = process_latex(full_response)
                        message_placeholder.markdown(formatted_response + "▌", unsafe_allow_html=True)
                        
                        # Force MathJax typesetting each time content is updated
                        force_mathjax_typeset()
                        time.sleep(0.01)  # Small delay for smoother appearance
                
                # Final update without the cursor
                formatted_response = process_latex(full_response)
                message_placeholder.markdown(formatted_response, unsafe_allow_html=True)
                
                # Final typesetting to ensure all math is rendered
                force_mathjax_typeset()
        
        except Exception as e:
            st.error(f"Error communicating with the agent: {str(e)}")
            full_response = f"Error: {str(e)}"
            message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Add a reset button
if st.button("Reset Chat"):
    st.session_state.messages = []
    st.session_state.conversation_id = str(uuid.uuid4())
    st.rerun()


