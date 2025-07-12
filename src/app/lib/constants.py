# Hard-coded model configurations
SUPPORT_OPENAI_MODELS = ["gpt-4.1-mini", "gpt-4.1"]
SUPPORT_GOOGLE_MODELS = ["gemini-flash", "gemini-2.5-pro"]
DEFAULT_MODEL = "gpt-4.1-mini"

BASIC_MODELS_PASSPORT = ["gpt-4.1-mini"]
PRO_MODELS_PASSPORT = ["gpt-4.1", "gemini-flash"]
ENTERPRISE_MODELS_PASSPORT = ["gemini-2.5-pro"]

BASIC_MCPS_PASSPORT = ["009ff9fb-1883-4d50-b5bf-b9135c116f73"]
PRO_MCPS_PASSPORT = []
ENTERPRISE_MCPS_PASSPORT = []

# Computed values
support_openai_models = SUPPORT_OPENAI_MODELS
support_google_models = SUPPORT_GOOGLE_MODELS
support_models = support_openai_models + support_google_models

default_model = DEFAULT_MODEL

basic_models_passport = BASIC_MODELS_PASSPORT
pro_models_passport = [*basic_models_passport, *PRO_MODELS_PASSPORT]
enterprise_models_passport = [
    *pro_models_passport,
    *ENTERPRISE_MODELS_PASSPORT,
]

models_passport = {
    "basic": basic_models_passport,
    "pro": pro_models_passport,
    "enterprise": enterprise_models_passport,
}

basic_mcps_passport = BASIC_MCPS_PASSPORT
pro_mcps_passport = [*basic_mcps_passport, *PRO_MCPS_PASSPORT]
enterprise_mcps_passport = [*pro_mcps_passport, *ENTERPRISE_MCPS_PASSPORT]

mcps_passport = {
    "basic": basic_mcps_passport,
    "pro": pro_mcps_passport,
    "enterprise": enterprise_mcps_passport,
}
