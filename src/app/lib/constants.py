from app.lib.config import get_settings

settings = get_settings()


support_openai_models = settings.support_openai_models

support_google_models = settings.support_google_models
support_models = support_openai_models + support_google_models

default_model = settings.default_model

basic_models_passport = settings.basic_models_passport

pro_models_passport = [*basic_models_passport, *settings.pro_models_passport]
enterprise_models_passport = [
    *pro_models_passport,
    *settings.enterprise_models_passport,
]

models_passport = {
    "basic": basic_models_passport,
    "pro": pro_models_passport,
    "enterprise": enterprise_models_passport,
}

basic_mcps_passport = settings.basic_mcps_passport
pro_mcps_passport = [*basic_mcps_passport, *settings.pro_mcps_passport]
enterprise_mcps_passport = [*pro_mcps_passport, *settings.enterprise_mcps_passport]

mcps_passport = {
    "basic": basic_mcps_passport,
    "pro": pro_mcps_passport,
    "enterprise": enterprise_mcps_passport,
}
