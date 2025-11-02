import yaml
from typing import Optional
from pathlib import Path


class Config:
    """Загрузчик конфигурации из YAML файла"""

    def __init__(self, config_path="config.yaml"):
        self.config_path = Path(config_path)
        self.package_name = None
        self.repository_url = None
        self.repository_mode = None
        self.package_version = None
        self.output_image = None
        self.ascii_tree_output = None
        self.max_depth = None
        self.filter_substring = None
        self.is_loaded = False

    def load_config(self):
        """Загружает конфигурацию из YAML файла"""
        if not self.config_path.exists():
            print(f"Конфигурационный файл {self.config_path} не найден")
            return
        if not self.config_path.is_file():
            print(f"{self.config_path} не является файлом")
            return
        with open(self.config_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
        if config_data is None:
            print("Конфигурационный файл пуст или имеет неверный формат")
            return
        self._validate_config(config_data)

    def _validate_config(self, config_data: dict):
        """Валидирует данные конфигурации"""
        required_fields = [
            'package_name', 'repository_url', 'repository_mode',
            'package_version', 'output_image', 'ascii_tree_output', 'max_depth'
        ]
        for field in required_fields:
            if field not in config_data:
                print(f"Обязательное поле '{field}' отсутствует в конфигурации")
                return
        if not isinstance(config_data['package_name'], str):
            print("package_name должен быть строкой")
            return
        if not isinstance(config_data['repository_url'], str):
            print("repository_url должен быть строкой")
            return
        if config_data['repository_mode'] not in ['remote', 'local']:
            print("repository_mode должен быть 'remote' или 'local'")
            return
        if not isinstance(config_data['package_version'], str):
            print("package_version должен быть строкой")
            return
        if not isinstance(config_data['output_image'], str):
            print("output_image должен быть строкой")
            return
        if not isinstance(config_data['ascii_tree_output'], bool):
            print("ascii_tree_output должен быть булевым значением")
            return
        if not isinstance(config_data['max_depth'], int) or config_data['max_depth'] < 1:
            print("max_depth должен быть целым числом больше 0")
            return
        self.package_name = config_data['package_name']
        self.repository_url = config_data['repository_url']
        self.repository_mode = config_data['repository_mode']
        self.package_version = config_data['package_version']
        self.output_image = config_data['output_image']
        self.ascii_tree_output = config_data['ascii_tree_output']
        self.max_depth = config_data['max_depth']
        self.filter_substring = config_data.get('filter_substring')
        self._is_loaded = True


def print_config(conf):
    """Выводит конфигурацию в формате ключ-значение"""
    if not conf.is_loaded:
        print("Конфигурация не загружена")
        return
    print("=" * 50)
    print("КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ")
    print("=" * 50)
    config_dict = {
        "Имя анализируемого пакета": conf.package_name,
        "URL репозитория/путь к файлу": conf.repository_url,
        "Режим работы с репозиторием": conf.repository_mode,
        "Версия пакета": conf.package_version,
        "Имя файла с изображением графа": conf.output_image,
        "Режим вывода ASCII-дерева": "Включен" if conf.ascii_tree_output else "Выключен",
        "Максимальная глубина анализа": conf.max_depth,
        "Подстрока для фильтрации пакетов": conf.filter_substring,
    }
    for key, value in config_dict.items():
        print(f"{key}: {value}")
    print("=" * 50)


config = Config('config.yaml')
config.load_config()
print_config(config)
