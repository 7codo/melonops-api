azure_api_version = "2025-01-01-preview"

support_openai_models = ["gpt-4.1-mini", "gpt-4.1"]
support_google_models = ["gemini-flash", "gemini-2.5-pro"]
default_model = "gpt-4.1-mini"
support_models = support_openai_models + support_google_models

# Computed values


free_models_passport = ["gpt-4.1-mini"]
starter_models_passport = [*free_models_passport, "gpt-4.1"]
pro_models_passport = [
    *starter_models_passport,
    "gemini-2.5-pro",
    "gemini-flash",
]

models_passport = {
    "free": free_models_passport,
    "starter": starter_models_passport,
    "pro": pro_models_passport,
}


free_mcps_passport = [
    "009ff9fb-1883-4d50-b5bf-b9135c116f73",
    "148434b1-bdc1-46e0-829f-fe2616fa2f75",
]
starter_mcps_passport = [*free_mcps_passport]
pro_mcps_passport = [*starter_mcps_passport]


mcps_passport = {
    "free": free_mcps_passport,
    "starter": starter_mcps_passport,
    "pro": pro_mcps_passport,
}

tokens_passport = {
    "free": {
        "gpt-4.1-mini": 25000,
        "gpt-4.1": 0,
        "gemini-flash": 0,
        "gemini-2.5-pro": 0,
    },
    "starter": {
        "gpt-4.1-mini": 25000,
        "gpt-4.1": 125000,
        "gemini-flash": 0,
        "gemini-2.5-pro": 0,
    },
    "pro": {
        "gpt-4.1-mini": 125000,
        "gpt-4.1": 125000,
        "gemini-flash": 125000,
        "gemini-2.5-pro": 125000,
    },
}

executions_passport = {
    "free": 5,
    "starter": 500,
    "pro": 10000,
}


admins = ["ayoub.7codo@gmail.com"]
