azure_api_version = "2025-01-01-preview"

support_openai_models = ["gpt-4.1"]
support_google_models = ["gemini-2.5-pro"]
default_model = "gpt-4.1"
support_models = support_openai_models + support_google_models

# Computed values


free_models_passport = ["gpt-4.1"]
starter_models_passport = [*free_models_passport, "gemini-2.5-pro"]
pro_models_passport = [
    *starter_models_passport,
]

models_passport = {
    "free": free_models_passport,
    "starter": starter_models_passport,
    "pro": pro_models_passport,
}


free_mcps_passport = [
    "a605a39a-b868-43b7-b226-1f0cb240f732",  # Notion
]
starter_mcps_passport = [
    *free_mcps_passport,
    "5b4e7741-0490-4325-bf84-d4549d6686cb",  # Web Search
]
pro_mcps_passport = [*starter_mcps_passport]


mcps_passport = {
    "free": free_mcps_passport,
    "starter": starter_mcps_passport,
    "pro": pro_mcps_passport,
}

tokens_passport = {
    "free": {
        "gpt-4.1": 500000,
        "gemini-2.5-pro": 0,
    },
    "starter": {
        "gpt-4.1": 1000000,
        "gemini-2.5-pro": 0,
    },
    "pro": {
        "gpt-4.1": 1000000,
        "gemini-2.5-pro": 1000000,
    },
}

executions_passport = {
    "free": 25,
    "starter": 1000,
    "pro": 100000,
}


admins = ["ayoub.7codo@gmail.com"]
