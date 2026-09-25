from apps.common.admin import register_models
from . import models

register_models(getattr(models, name) for name in models.__all__)
