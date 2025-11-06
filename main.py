import yaml
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional


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
        self.is_loaded = True


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

class DependencyAnalyzer:
    def __init__(self, repo_url: str, repo_mode: str = 'remote'):
        self.repo_url = repo_url.rstrip('/')
        self.repo_mode = repo_mode

    def get_direct_dependencies(self, package_name, version):
        """Получает прямые зависимости для указанного пакета и версии"""
        try:
            if self.repo_mode == 'remote':
                return self._get_remote_dependencies(package_name, version)
            else:
                return self._get_local_dependencies(package_name, version)
        except Exception as e:
            print(f"Ошибка при получении зависимостей: {e}")

    def _get_remote_dependencies(self, package_name, version):
        """Получает зависимости из удаленного Maven репозитория"""
        if ':' not in package_name:
            print(f"Неверный формат имени пакета: {package_name}. Ожидается формат 'groupId:artifactId'")
            return None
        group_id, artifact_id = package_name.split(':', 1)
        group_path = group_id.replace('.', '/')
        pom_url = f"{self.repo_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
        try:
            with urllib.request.urlopen(pom_url) as response:
                pom_content = response.read().decode('utf-8')
            return self._parse_pom_dependencies(pom_content)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"POM файл не найден по URL: {pom_url}")
            else:
                print(f"HTTP ошибка {e.code} при загрузке POM: {e.reason}")
        except urllib.error.URLError as e:
            print(f"Ошибка URL при загрузке POM: {e.reason}")
        except UnicodeDecodeError:
            print("Ошибка декодирования POM файла")

    def _get_local_dependencies(self, package_name, version):
        print("Локальный режим пока не поддерживается")

    def _parse_pom_dependencies(self, pom_content):
        """Парсит зависимости из POM XML содержимого"""
        try:
            root = ET.fromstring(pom_content)
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            dependencies = []
            deps_element = root.find('.//maven:dependencies', ns)
            if deps_element is not None:
                for dep_element in deps_element.findall('maven:dependency', ns):
                    dependency = self._parse_dependency_element(dep_element, ns)
                    if dependency and self._is_runtime_dependency(dependency):
                        dependencies.append(dependency)
            return dependencies
        except ET.ParseError as e:
            print(f"Ошибка парсинга POM XML: {e}")

    def _parse_dependency_element(self, dep_element, ns):
        """Парсит элемент dependency и возвращает информацию о зависимости"""
        group_id_elem = dep_element.find('maven:groupId', ns)
        artifact_id_elem = dep_element.find('maven:artifactId', ns)
        version_elem = dep_element.find('maven:version', ns)
        scope_elem = dep_element.find('maven:scope', ns)
        type_elem = dep_element.find('maven:type', ns)
        optional_elem = dep_element.find('maven:optional', ns)
        if group_id_elem is not None and artifact_id_elem is not None:
            dependency = {
                'groupId': group_id_elem.text,
                'artifactId': artifact_id_elem.text,
                'version': version_elem.text if version_elem is not None else 'N/A',
                'scope': scope_elem.text if scope_elem is not None else 'compile',
                'type': type_elem.text if type_elem is not None else 'jar',
                'optional': optional_elem.text if optional_elem is not None else 'false',
                'full_name': f"{group_id_elem.text}:{artifact_id_elem.text}"
            }
            return dependency
        return None

    def _is_runtime_dependency(self, dependency):
        """Проверяет, является ли зависимость реальной runtime зависимостью"""
        if dependency['scope'] == 'import':
            return False
        if dependency['optional'].lower() == 'true':
            return False
        if dependency['type'] != 'jar':
            return False
        valid_scopes = ['compile', 'runtime', None]
        return dependency['scope'] in valid_scopes

    def format_dependencies_output(self, dependencies: List[Dict[str, str]]) -> str:
        """Форматирует вывод зависимостей для отображения"""
        if not dependencies:
            return "Прямые зависимости не найдены"
        output = ["Прямые зависимости:"]
        output.append("-" * 50)
        for i, dep in enumerate(dependencies, 1):
            output.append(f"{i}. {dep['full_name']}:{dep['version']}")
            if dep['scope'] != 'compile':
                output.append(f"   Scope: {dep['scope']}")
            if dep['type'] != 'jar':
                output.append(f"   Type: {dep['type']}")
            if dep['optional'] == 'true':
                output.append(f"   Optional: {dep['optional']}")
            output.append("")
        return "\n".join(output)

config = Config('config.yaml')
config.load_config()
print_config(config)

analyzer = DependencyAnalyzer(
    repo_url=config.repository_url,
    repo_mode=config.repository_mode
)

print(f"Анализ зависимостей для пакета: {config.package_name}:{config.package_version}")
print(f"Репозиторий: {config.repository_url}")
print()
dependencies = analyzer.get_direct_dependencies(
    package_name=config.package_name,
    version=config.package_version
)
print(analyzer.format_dependencies_output(dependencies))
