"""
app.py - Bharat Connect Language-First UI
==========================================
Complete multilingual interface supporting 10 Indian languages

Supported Languages:
- Hindi, English, Telugu, Tamil, Marathi
- Gujarati, Kannada, Malayalam, Bengali, Punjabi

Author: Bharat Connect Team
Date: 2025-10-25
"""

import streamlit as st
from agents.bharat_agent import BharatConnectAgent
import os
from google.oauth2 import service_account  # ADD THIS
import vertexai  # ADD THIS

# ============================================================================
# GOOGLE CLOUD CREDENTIALS SETUP (FOR STREAMLIT CLOUD)
# ============================================================================

def init_google_cloud():
    """Initialize Google Cloud credentials for both local and cloud deployment"""
    
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        # Running on Streamlit Cloud - use secrets
        print("✅ Using Streamlit Cloud secrets")
        
        os.environ['GCP_PROJECT_ID'] = st.secrets["GCP_PROJECT_ID"]
        os.environ['GCP_LOCATION'] = st.secrets["GCP_LOCATION"]
        
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform",
                "https://www.googleapis.com/auth/bigquery"
            ]
        )
        
        vertexai.init(
            project=st.secrets["GCP_PROJECT_ID"],
            location=st.secrets["GCP_LOCATION"],
            credentials=credentials
        )
        
        return credentials
    else:
        # Running locally
        print("✅ Using local .env file")
        from dotenv import load_dotenv
        load_dotenv()
        return None

# Initialize on app start
init_google_cloud()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Bharat Connect | भारत कनेक्ट",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# COMPLETE LANGUAGE CONFIGURATION (10 Languages)
# ============================================================================

LANGUAGES = {
    'hi': {
        'name': 'Hindi',
        'native': 'हिंदी',
        'greeting': 'नमस्ते! आप क्या खोज रहे हैं?',
        'search_placeholder': 'यहां खोजें...',
        'search_button': 'खोजें',
        'results_title': 'परिणाम',
        'original_language': 'मूल भाषा',
        'translated_note': '(अनुवादित)',
        'no_results': 'कोई परिणाम नहीं मिला',
        'news': 'समाचार',
        'education': 'शिक्षा',
        'change_language': 'भाषा बदलें',
        'searching': 'खोज रहे हैं...',
        'color': '#FF9933'
    },
    'en': {
        'name': 'English',
        'native': 'English',
        'greeting': 'Hello! What are you looking for?',
        'search_placeholder': 'Search here...',
        'search_button': 'Search',
        'results_title': 'Results',
        'original_language': 'Original Language',
        'translated_note': '(Translated)',
        'no_results': 'No results found',
        'news': 'News',
        'education': 'Education',
        'change_language': 'Change Language',
        'searching': 'Searching...',
        'color': '#FFFFFF'
    },
    'te': {
        'name': 'Telugu',
        'native': 'తెలుగు',
        'greeting': 'నమస్కారం! మీరు ఏమి వెతుకుతున్నారు?',
        'search_placeholder': 'ఇక్కడ వెతకండి...',
        'search_button': 'వెతకండి',
        'results_title': 'ఫలితాలు',
        'original_language': 'అసలు భాష',
        'translated_note': '(అనువదించబడింది)',
        'no_results': 'ఫలితాలు కనుగొనబడలేదు',
        'news': 'వార్తలు',
        'education': 'విద్య',
        'change_language': 'భాషను మార్చండి',
        'searching': 'వెతుకుతోంది...',
        'color': '#138808'
    },
    'ta': {
        'name': 'Tamil',
        'native': 'தமிழ்',
        'greeting': 'வணக்கம்! நீங்கள் எதைத் தேடுகிறீர்கள்?',
        'search_placeholder': 'இங்கே தேடுங்கள்...',
        'search_button': 'தேடு',
        'results_title': 'முடிவுகள்',
        'original_language': 'அசல் மொழி',
        'translated_note': '(மொழிபெயர்க்கப்பட்டது)',
        'no_results': 'முடிவுகள் இல்லை',
        'news': 'செய்திகள்',
        'education': 'கல்வி',
        'change_language': 'மொழியை மாற்று',
        'searching': 'தேடுகிறது...',
        'color': '#FF9933'
    },
    'mr': {
        'name': 'Marathi',
        'native': 'मराठी',
        'greeting': 'नमस्कार! तुम्ही काय शोधत आहात?',
        'search_placeholder': 'येथे शोधा...',
        'search_button': 'शोधा',
        'results_title': 'परिणाम',
        'original_language': 'मूळ भाषा',
        'translated_note': '(भाषांतरित)',
        'no_results': 'परिणाम सापडले नाहीत',
        'news': 'बातम्या',
        'education': 'शिक्षण',
        'change_language': 'भाषा बदला',
        'searching': 'शोधत आहे...',
        'color': '#138808'
    },
    'gu': {
        'name': 'Gujarati',
        'native': 'ગુજરાતી',
        'greeting': 'નમસ્તે! તમે શું શોધી રહ્યા છો?',
        'search_placeholder': 'અહીં શોધો...',
        'search_button': 'શોધો',
        'results_title': 'પરિણામો',
        'original_language': 'મૂળ ભાષા',
        'translated_note': '(અનુવાદિત)',
        'no_results': 'કોઈ પરિણામ મળ્યાં નથી',
        'news': 'સમાચાર',
        'education': 'શિક્ષણ',
        'change_language': 'ભાષા બદલો',
        'searching': 'શોધી રહ્યું છે...',
        'color': '#FF9933'
    },
    'kn': {
        'name': 'Kannada',
        'native': 'ಕನ್ನಡ',
        'greeting': 'ನಮಸ್ಕಾರ! ನೀವು ಏನು ಹುಡುಕುತ್ತಿದ್ದೀರಿ?',
        'search_placeholder': 'ಇಲ್ಲಿ ಹುಡುಕಿ...',
        'search_button': 'ಹುಡುಕಿ',
        'results_title': 'ಫಲಿತಾಂಶಗಳು',
        'original_language': 'ಮೂಲ ಭಾಷೆ',
        'translated_note': '(ಅನುವಾದಿಸಲಾಗಿದೆ)',
        'no_results': 'ಫಲಿತಾಂಶಗಳು ಕಂಡುಬಂದಿಲ್ಲ',
        'news': 'ಸುದ್ದಿ',
        'education': 'ಶಿಕ್ಷಣ',
        'change_language': 'ಭಾಷೆ ಬದಲಾಯಿಸಿ',
        'searching': 'ಹುಡುಕಲಾಗುತ್ತಿದೆ...',
        'color': '#138808'
    },
    'ml': {
        'name': 'Malayalam',
        'native': 'മലയാളം',
        'greeting': 'നമസ്കാരം! നിങ്ങൾ എന്താണ് തിരയുന്നത്?',
        'search_placeholder': 'ഇവിടെ തിരയുക...',
        'search_button': 'തിരയുക',
        'results_title': 'ഫലങ്ങൾ',
        'original_language': 'യഥാർത്ഥ ഭാഷ',
        'translated_note': '(പരിഭാഷപ്പെടുത്തിയത്)',
        'no_results': 'ഫലങ്ങളൊന്നും കണ്ടെത്തിയില്ല',
        'news': 'വാർത്തകൾ',
        'education': 'വിദ്യാഭ്യാസം',
        'change_language': 'ഭാഷ മാറ്റുക',
        'searching': 'തിരയുന്നു...',
        'color': '#FF9933'
    },
    'bn': {
        'name': 'Bengali',
        'native': 'বাংলা',
        'greeting': 'নমস্কার! আপনি কী খুঁজছেন?',
        'search_placeholder': 'এখানে খুঁজুন...',
        'search_button': 'খুঁজুন',
        'results_title': 'ফলাফল',
        'original_language': 'মূল ভাষা',
        'translated_note': '(অনুবাদ করা)',
        'no_results': 'কোন ফলাফল পাওয়া যায়নি',
        'news': 'খবর',
        'education': 'শিক্ষা',
        'change_language': 'ভাষা পরিবর্তন করুন',
        'searching': 'খুঁজছি...',
        'color': '#138808'
    },
    'pa': {
        'name': 'Punjabi',
        'native': 'ਪੰਜਾਬੀ',
        'greeting': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਤੁਸੀਂ ਕੀ ਖੋਜ ਰਹੇ ਹੋ?',
        'search_placeholder': 'ਇੱਥੇ ਖੋਜੋ...',
        'search_button': 'ਖੋਜੋ',
        'results_title': 'ਨਤੀਜੇ',
        'original_language': 'ਅਸਲ ਭਾਸ਼ਾ',
        'translated_note': '(ਅਨੁਵਾਦ ਕੀਤਾ)',
        'no_results': 'ਕੋਈ ਨਤੀਜੇ ਨਹੀਂ ਮਿਲੇ',
        'news': 'ਖ਼ਬਰਾਂ',
        'education': 'ਸਿੱਖਿਆ',
        'change_language': 'ਭਾਸ਼ਾ ਬਦਲੋ',
        'searching': 'ਖੋਜ ਰਿਹਾ ਹੈ...',
        'color': '#FF9933'
    }
}

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Result card styling */
    .result-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #FF9933;
        transition: transform 0.2s ease;
    }
    
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Translation badge */
    .translated-badge {
        background: linear-gradient(90deg, #FFF3CD, #FFF8E1);
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        color: #856404;
        display: inline-block;
        margin-bottom: 10px;
        border: 1px solid #FFE69C;
    }
    
    /* Language button styling */
    .stButton > button {
        font-size: 24px;
        font-weight: bold;
        padding: 20px;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'selected_language' not in st.session_state:
    st.session_state.selected_language = None

if 'agent' not in st.session_state:
    st.session_state.agent = None

# ============================================================================
# LANGUAGE SELECTION PAGE
# ============================================================================

def language_selection_page():
    """Beautiful landing page with all 10 language options."""
    
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <h1 style="font-size: 52px; margin-bottom: 10px;">🇮🇳 भारत कनेक्ट</h1>
        <h2 style="font-size: 36px; color: #666; margin-bottom: 20px;">Bharat Connect</h2>
        <p style="font-size: 20px; color: #888; margin-bottom: 50px;">
            Bridging India's Digital Language Divide
        </p>
        <p style="font-size: 18px; color: #999;">
            Choose your language | अपनी भाषा चुनें | మీ భాషను ఎంచుకోండి
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center; color: #666; margin: 30px 0;'>Select Your Language</h3>", unsafe_allow_html=True)
    
    # Create 2 rows of 5 languages each
    row1 = list(LANGUAGES.items())[:5]
    row2 = list(LANGUAGES.items())[5:]
    
    # Row 1
    cols1 = st.columns(5)
    for idx, (lang_code, lang_data) in enumerate(row1):
        with cols1[idx]:
            if st.button(
                lang_data['native'],
                key=f"lang_{lang_code}",
                use_container_width=True,
                type="primary" if lang_code == 'en' else "secondary"
            ):
                st.session_state.selected_language = lang_code
                st.rerun()
    
    # Row 2
    cols2 = st.columns(5)
    for idx, (lang_code, lang_data) in enumerate(row2):
        with cols2[idx]:
            if st.button(
                lang_data['native'],
                key=f"lang_{lang_code}",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.selected_language = lang_code
                st.rerun()
    
    st.markdown("""
    <div style="text-align: center; margin-top: 80px;">
        <h3 style="color: #666; margin-bottom: 20px;">What Makes Us Special</h3>
        <div style="display: flex; justify-content: center; gap: 40px; flex-wrap: wrap; max-width: 1000px; margin: 0 auto;">
            <div style="text-align: center; flex: 1; min-width: 200px;">
                <h2 style="color: #FF9933; margin-bottom: 10px;">10</h2>
                <p style="color: #888;">Indian Languages</p>
            </div>
            <div style="text-align: center; flex: 1; min-width: 200px;">
                <h2 style="color: #138808; margin-bottom: 10px;">1000+</h2>
                <p style="color: #888;">Content Sources</p>
            </div>
            <div style="text-align: center; flex: 1; min-width: 200px;">
                <h2 style="color: #FF9933; margin-bottom: 10px;">AI</h2>
                <p style="color: #888;">Powered Translation</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-top: 60px; color: #999; font-size: 14px;">
        <p>Built for Google Cloud AI Hackathon 2025</p>
        <p>Powered by Vertex AI • Fivetran • BigQuery</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION PAGE
# ============================================================================

def main_app_page(lang_code):
    """Main application interface in selected language."""
    
    lang = LANGUAGES[lang_code]
    
    # Initialize agent if needed
    if st.session_state.agent is None:
        with st.spinner(f"{lang['searching']}"):
            PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'bharat-connect-000')
            LOCATION = os.getenv('GCP_LOCATION', 'us-central1')
            st.session_state.agent = BharatConnectAgent(
                project_id=PROJECT_ID,
                location=LOCATION,
                user_language=lang['name']
            )
    
    agent = st.session_state.agent
    
    # Header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"# 🇮🇳 {lang['native']}")
        st.markdown(f"*{lang['greeting']}*")
    with col2:
        if st.button(f"{lang['change_language']}", key="change_lang"):
            st.session_state.selected_language = None
            st.session_state.agent = None
            st.rerun()
    
    st.divider()
    
    # Search interface
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Search",
            placeholder=lang['search_placeholder'],
            label_visibility="collapsed",
            key="search_input"
        )
    
    with col2:
        search_btn = st.button(
            f"{lang['search_button']}",
            type="primary",
            use_container_width=True,
            key="search_btn"
        )
    
    # Search execution
    if search_btn and query:
        with st.spinner(f"{lang['searching']}"):
            response = agent.process_query(query)
        
        if "error" in response:
            st.error(f"{response['error']}")
        
        elif response.get("results"):
            st.success(f"{response['results_count']} {lang['results_title']}")
            
            # Show cross-language note if applicable
            if response.get('cross_language_used'):
                st.info(f"ℹResults from other languages translated to {lang['native']}")
            
            # Display results
            for idx, result in enumerate(response['results'], 1):
                with st.container():
                    st.markdown(f"### {idx}. {result['title']}")
                    
                    # Show translation badge if content is from different language
                    if result.get('was_translated'):
                        st.markdown(f"""
                        <span class="translated-badge">
                            {lang['original_language']}: {result['original_language']} {lang['translated_note']}
                        </span>
                        """, unsafe_allow_html=True)
                    
                    # Summary
                    st.write(result['summary'])
                    
                    st.divider()
                    
                    # Metadata
                    cols = st.columns(4)
                    with cols[0]:
                        st.caption(f"**Source:** {result['source']}")
                    with cols[1]:
                        content_type_label = lang['news'] if result['content_type'] == 'news' else lang['education']
                        st.caption(f"**Type:** {content_type_label}")
                    with cols[2]:
                        st.caption(f"**Date:** {result['date'][:10]}")
                    with cols[3]:
                        st.markdown(f"[Link]({result['url']})")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
        
        else:
            st.warning(f"{lang['no_results']}")
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; font-size: 12px;">
        <p>Built for Digital India 🇮🇳 | Google Cloud AI Hackathon 2025</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN ROUTER
# ============================================================================

def main():
    """Main application router."""
    
    if st.session_state.selected_language is None:
        language_selection_page()
    else:
        main_app_page(st.session_state.selected_language)

if __name__ == "__main__":
    main()
