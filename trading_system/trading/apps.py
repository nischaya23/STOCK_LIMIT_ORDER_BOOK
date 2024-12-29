# from django.apps import AppConfig


# class TradingConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "trading"

from django.apps import AppConfig

class TradingConfig(AppConfig):
    name = 'trading'

    def ready(self):
        import trading.signals
