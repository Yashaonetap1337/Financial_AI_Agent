import streamlit as st
import os
from datetime import datetime
from Financial_Agent import Financial_Agent

# # Streamlit UI
st.set_page_config(
    page_title="Финансовый AI-ассистент",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стили CSS для красивого оформления
st.markdown("""
<style>
    .stTextInput input, .stTextArea textarea {
        border-radius: 10px !important;
        padding: 10px !important;
    }
    .stButton button {
        width: 100%;
        border-radius: 10px;
        padding: 10px;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #45a049;
    }
    .response-box {
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        background-color: #f0f2f6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .highlight {
        background-color: #e6f7ff;
        padding: 15px;
        border-left: 4px solid #1890ff;
        border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Заголовок с анимацией
st.markdown("""
<h1 style='text-align: center; color: #2c3e50; margin-bottom: 30px;'>
    💼 Финансовый AI-ассистент
</h1>
""", unsafe_allow_html=True)

# Боковая панель для настроек
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Примеры запросов")
    examples = [
        "Сколько я потратил в январе 2025 в рублях?",
        "Конвертируй 1000 USD в RUB",
        "Покажи все траты за последний месяц",
        "Рассчитай (500 + 250) * 0.2"
    ]
    for example in examples:
        if st.button(example, key=example):
            st.session_state.example_query = example


# Основная область ввода
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_area(
        "📝 Введите ваш запрос:",
        height=150,
        value=st.session_state.get('example_query', ''),
        placeholder="Например: 'Сколько я потратил в январе 2025 в рублях?'"
    )

with col2:
    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
    if st.button("🚀 Выполнить запрос"):
        st.session_state.run_query = True

# Обработка запроса
if st.session_state.get('run_query', False):
    if not query.strip():
        st.warning("⚠️ Пожалуйста, введите запрос.")
    else:
        with st.spinner("🔄 Обрабатываю запрос..."):
            try:
                start_time = datetime.now()
                
                # Выполнение запроса
                response = Financial_Agent.run(query)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Отображение результата
                st.markdown("---")
                st.markdown(f"### 📅 Результат запроса ({processing_time:.2f} сек)")
                
                if isinstance(response, dict) and 'arguments' in response:
                    answer = response['arguments'].get('answer', '')
                    st.markdown(f"""
                    <div class="highlight">
                        <h4 style='margin-top:0;'>{answer}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="response-box">
                        {response}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Дополнительная информация
                with st.expander("🔍 Подробности выполнения"):
                    st.json(response)
                
                # Сохранение в историю
                if 'history' not in st.session_state:
                    st.session_state.history = []
                
                st.session_state.history.insert(0, {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'query': query,
                    'response': answer if isinstance(response, dict) else str(response)
                })
                
            except Exception as e:
                st.error(f"❌ Ошибка при выполнении запроса: {str(e)}")

# История запросов
if 'history' in st.session_state and st.session_state.history:
    st.markdown("---")
    st.markdown("### 📜 История запросов")
    
    for i, item in enumerate(st.session_state.history[:5]):  # Показываем последние 5 запросов
        with st.expander(f"{i+1}. {item['query']} ({item['timestamp']})"):
            st.markdown(f"**Запрос:** `{item['query']}`")
            st.markdown(f"**Ответ:** {item['response']}")