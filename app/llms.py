from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.config import GEMINI_API_KEY, GROQ_API_KEY
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# ... bloco MODELOS copiado do graph.py, com api_key=GEMINI_API_KEY / GROQ_API_KEY
# llm_gemini, llm_groq, llm_rapido — mesmos nomes, mesmos model= e temperature=

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    top_p=0.95,
    api_key=GEMINI_API_KEY,
)
llm_groq = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    api_key=GROQ_API_KEY,
)

llm_rapido = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.0,
    api_key=GROQ_API_KEY,
)

embedding = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        google_api_key=GEMINI_API_KEY
)

llm_especialista = llm_gemini.with_fallbacks([llm_groq])   # se o Gemini falhar, o Groq assume