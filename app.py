import time
import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE


# -----------------------------
# Page setup
# -----------------------------

st.set_page_config(
    page_title="Snap & Study",
    page_icon="📚",
    layout="centered"
)


# -----------------------------
# Gemini API key
# -----------------------------

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


# -----------------------------
# Gemini client
# -----------------------------

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()


# -----------------------------
# Chat history
# -----------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# -----------------------------
# Gemini request with retry
# -----------------------------

def generate_answer(contents):

    models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    last_error = None

    for model in models:

        for attempt in range(3):

            try:

                response = gemini_client.models.generate_content(
                    model=model,
                    contents=contents
                )

                return response

            except Exception as error:

                last_error = error
                error_text = str(error)

                # Retry temporary 503 errors
                if "503" in error_text or "UNAVAILABLE" in error_text:

                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue

                    break

                # Try next model if unavailable
                if "404" in error_text or "NOT_FOUND" in error_text:
                    break

                # Do not retry other errors
                raise error

    raise last_error


# -----------------------------
# Main application
# -----------------------------

st.title("📚 Snap & Study")
st.caption("Snap it. Understand it. Learn it.")

st.write(
    "Upload a study question, textbook page, diagram or notes, "
    "and I'll explain it in simple language."
)


# -----------------------------
# Name
# -----------------------------

if "name" not in st.session_state:
    st.session_state.name = "Student"


name = st.text_input(
    "Your name",
    value=st.session_state.name
)

st.session_state.name = name


# -----------------------------
# Welcome message
# -----------------------------

if "welcome_shown" not in st.session_state:

    st.info(
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        )
    )

    st.session_state.welcome_shown = True


# -----------------------------
# Display previous chat history
# -----------------------------

for message in st.session_state.chat_history:

    if message["role"] == "user":

        with st.chat_message("user"):
            st.write(message["text"])

    elif message["role"] == "assistant":

        with st.chat_message("assistant"):
            st.write(message["text"])


# -----------------------------
# Chat input + file attachment
# -----------------------------

chat_input = st.chat_input(
    "Ask a study question...",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp"]
)


# -----------------------------
# Process chat input
# -----------------------------

if chat_input:

    user_text = chat_input.text
    uploaded_files = chat_input.files

    # -------------------------
    # Save user's question
    # -------------------------

    if user_text:

        st.session_state.chat_history.append({
            "role": "user",
            "text": user_text
        })

    # -------------------------
    # Display user's question
    # -------------------------

    if user_text:

        with st.chat_message("user"):
            st.write(user_text)


    # -------------------------
    # Process uploaded image
    # -------------------------

    if uploaded_files:

        uploaded_file = uploaded_files[0]

        st.image(
            uploaded_file,
            caption="Uploaded study material",
            use_container_width=True
        )


    # -------------------------
    # Send to Gemini
    # -------------------------

    with st.spinner("Thinking..."):

        try:

            # -------------------------
            # Image + text
            # -------------------------

            if uploaded_files:

                uploaded_file = uploaded_files[0]

                image_bytes = uploaded_file.getvalue()

                prompt = SYSTEM_PROMPT

                if user_text:

                    prompt += (
                        "\n\nStudent's question:\n"
                        + user_text
                    )

                prompt += (
                    "\n\nRead the uploaded image carefully and "
                    "explain the study material in simple language."
                )

                response = generate_answer(
                    [
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type
                        ),
                        prompt
                    ]
                )


            # -------------------------
            # Text only
            # -------------------------

            elif user_text:

                response = generate_answer(
                    [
                        SYSTEM_PROMPT,
                        user_text
                    ]
                )


            # -------------------------
            # Nothing entered
            # -------------------------

            else:

                response = None


            # -------------------------
            # Display and save answer
            # -------------------------

            if response and response.text:

                answer = response.text

                with st.chat_message("assistant"):
                    st.write(answer)

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "text": answer
                })

            else:

                st.warning(
                    "I couldn't generate an answer. "
                    "Please try again."
                )


        except Exception as error:

            st.error(
                f"Gemini error: {error}"
            )