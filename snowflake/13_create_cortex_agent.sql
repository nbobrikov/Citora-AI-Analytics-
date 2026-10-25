-- Create the Citora AI assistant and attach Cortex Analyst to the semantic view.
-- Run after 12_register_semantic_view.sql and the CITORA_ANALYST grants.

USE ROLE CITORA_ANALYST;
USE WAREHOUSE CITORA_ANALYTICS_WH;
USE DATABASE CITORA;
USE SCHEMA ANALYTICS;

CREATE OR REPLACE AGENT CITORA.ANALYTICS.CITORA_AI_ANALYST
    COMMENT = 'AI assistant for Citora business metrics and analytical reporting'
    PROFILE = '{"display_name": "Citora AI Analyst"}'
    FROM SPECIFICATION
    $$
    models:
      orchestration: auto

    orchestration:
      tool_not_accessible: reject
      budget:
        seconds: 60
        tokens: 16000

    instructions:
      response: >-
        Отвечай на русском языке, кратко и по существу. Всегда называй
        использованный отчетный период. Процентные метрики отображай как
        проценты: значение 0.25 показывай как 25%. Не складывай лиды и другие
        неаддитивные показатели между группами. Если вопрос неоднозначен,
        сначала уточни период или необходимый разрез.
      orchestration: >-
        Для любых вопросов о лидах, заявках, продажах, конверсии, времени
        конверсии, доле Самотока, разметке, источниках, сегментах, менеджерах,
        продуктах и воронках обязательно используй инструмент Citora_Analyst.
        Не придумывай значения и не отвечай на такие вопросы из общих знаний.
      sample_questions:
        - question: "Покажи все основные метрики за март 2025 года."
        - question: "Сколько было лидов и продаж по источникам за март 2025 года?"
        - question: "Какая конверсия заявок в продажи по менеджерам?"
        - question: "Как менялась доля Самотока по месяцам?"

    tools:
      - tool_spec:
          type: "cortex_analyst_text_to_sql"
          name: "Citora_Analyst"
          description: >-
            Рассчитывает утвержденные метрики Citora по единой отчетной дате
            и формирует SQL через CITORA_ANALYTICS_SEMANTIC_VIEW.

    tool_resources:
      Citora_Analyst:
        semantic_view: "CITORA.ANALYTICS.CITORA_ANALYTICS_SEMANTIC_VIEW"
        execution_environment:
          type: "warehouse"
          warehouse: "CITORA_ANALYTICS_WH"
    $$;

DESCRIBE AGENT CITORA.ANALYTICS.CITORA_AI_ANALYST;
