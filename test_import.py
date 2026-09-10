from common import BaseSettings, setup_logging, JWTService

print("✅ All imports from common work!")

# Проверяем настройки
class TestSettings(BaseSettings):
    pass

settings = TestSettings()
print(f"✅ Settings loaded: SERVICE_NAME={settings.SERVICE_NAME}")
