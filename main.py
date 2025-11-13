import os

import yaml
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Any


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
        self.test_graph = None

    def get_dependencies(self, package_name, version):
        """Получает зависимости для указанного пакета и версии"""
        try:
            if self.repo_mode == 'remote':
                return self._get_remote_dependencies(package_name, version)
            elif self.repo_mode == 'local':
                return self._get_local_dependencies(package_name, version)
            elif self.repo_mode == 'test':
                return self._get_test_dependencies(package_name, version)
            else:
                print(f"Неподдерживаемый режим репозитория: {self.repo_mode}")
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
        """Получает зависимости из локального тестового файла"""
        if self.test_graph is None:
            self._load_test_graph()
        if package_name not in self.test_graph:
            return []
        dependencies = []
        for dep_name in self.test_graph[package_name]:
            dependencies.append({
                'groupId': dep_name,
                'artifactId': dep_name,
                'version': '1.0.0',
                'scope': 'compile',
                'type': 'jar',
                'optional': 'false',
                'full_name': dep_name
            })
        return dependencies

    def _get_test_dependencies(self, package_name, version):
        return self._get_local_dependencies(package_name, version)

    def _load_test_graph(self):
        """Загружает тестовый граф из YAML файла"""
        try:
            if not os.path.exists(self.repo_url):
                print(f"Тестовый файл не найден: {self.repo_url}")
            with open(self.repo_url, 'r', encoding='utf-8') as file:
                graph_data = yaml.safe_load(file)
            if not isinstance(graph_data, dict):
                print("Тестовый файл должен содержать словарь")
            self.test_graph = {}
            for package, deps in graph_data.items():
                if not isinstance(package, str):
                    print("Ключи в тестовом файле должны быть строками")
                if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
                    print("Значения в тестовом файле должны быть списками строк")
                self.test_graph[package] = deps
        except yaml.YAMLError as e:
            print(f"Ошибка парсинга тестового YAML: {e}")
        except IOError as e:
            print(f"Ошибка чтения тестового файла: {e}")

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

    def format_dependencies_output(self, dependencies: List[Dict[str, str]]):
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


class GraphBuilder:
    """Класс для построения графа зависимостей с использованием BFS с рекурсией"""

    def __init__(self, analyzer: Any, max_depth=3, filter_substring=""):
        self.analyzer = analyzer
        self.max_depth = max_depth
        self.filter_substring = filter_substring.lower()
        self.visited = {}
        self.dependency_graph = {}
        self.cyclic_dependencies = set()
        self.load_order = []

    def build_dependency_graph(self, root_package, root_version):
        """Строит полный граф зависимостей"""
        self.visited.clear()
        self.dependency_graph.clear()
        self.cyclic_dependencies.clear()
        self._bfs_with_recursion([(root_package, root_version, 0)])
        return {
            'graph': self.dependency_graph,
            'depths': self.visited,
            'cyclic_dependencies': list(self.cyclic_dependencies),
            'total_packages': len(self.dependency_graph),
            'total_dependencies': sum(len(deps) for deps in self.dependency_graph.values()),
            'load_order': self.load_order
        }

    def _bfs_with_recursion(self, queue: List[Tuple[str, str, int]]):
        """BFS с рекурсивной обработкой зависимостей"""
        if not queue:
            return
        next_level_queue = []
        for package, version, depth in queue:
            package_key = f"{package}:{version}"
            if package_key in self.visited or depth >= self.max_depth:
                continue
            self.visited[package_key] = depth
            self.load_order.append(package_key)
            try:
                dependencies = self.analyzer.get_dependencies(package, version)
                filtered_dependencies = self._filter_dependencies(dependencies)
                self.dependency_graph[package_key] = [
                    f"{dep['full_name']}:{dep['version']}" for dep in filtered_dependencies
                ]
                for dep in filtered_dependencies:
                    dep_key = f"{dep['full_name']}:{dep['version']}"
                    if dep_key in self.visited:
                        cycle = tuple(sorted([package_key, dep_key]))
                        self.cyclic_dependencies.add(cycle)
                        continue
                    next_level_queue.append((dep['full_name'], dep['version'], depth + 1))
            except Exception as e:
                self.dependency_graph[package_key] = []
        self._bfs_with_recursion(next_level_queue)

    def _filter_dependencies(self, dependencies):
        """Фильтрует зависимости по подстроке"""
        if not self.filter_substring:
            return dependencies
        filtered = []
        for dep in dependencies:
            if self.filter_substring not in dep['full_name'].lower():
                filtered.append(dep)
        return filtered

    def format_graph_output(self, graph_data: Dict[str, Any]) -> str:
        """Форматирует вывод графа зависимостей"""
        graph = graph_data['graph']
        depths = graph_data['depths']
        cyclic_deps = graph_data['cyclic_dependencies']
        load_order = graph_data['load_order']
        output = []
        output.append("=== ГРАФ ЗАВИСИМОСТЕЙ ===")
        output.append(f"Всего пакетов: {graph_data['total_packages']}")
        output.append(f"Всего зависимостей: {graph_data['total_dependencies']}")
        output.append(f"Циклические зависимости: {len(cyclic_deps)}")
        output.append("")
        if cyclic_deps:
            output.append("Обнаружены циклические зависимости:")
            for cycle in cyclic_deps:
                output.append(f"  Цикл: {cycle[0]} <-> {cycle[1]}")
            output.append("")
        output.append("Структура графа:")
        output.append("-" * 50)

        output.append("Порядок загрузки зависимостей (BFS):")
        for i, package in enumerate(load_order, 1):
            output.append(f"  {i}. {package}")
        output.append("")

        output.append("Структура графа:")
        output.append("-" * 50)

        sorted_packages = sorted(graph.keys(), key=lambda p: depths.get(p, 0))
        for package in sorted_packages:
            depth = depths.get(package, 0)
            dependencies = graph[package]
            output.append(f"{package} (глубина: {depth})")
            if dependencies:
                for dep in dependencies:
                    dep_depth = depths.get(dep, self.max_depth)
                    output.append(f"   └── {dep} (глубина: {dep_depth})")
            else:
                output.append("   └── (нет зависимостей)")
            output.append("")
        return "\n".join(output)


config = Config('test_config.yaml')
config.load_config()
print_config(config)

analyzer = DependencyAnalyzer(
    repo_url=config.repository_url,
    repo_mode=config.repository_mode
)
print(f"Анализ зависимостей для пакета: {config.package_name}:{config.package_version}")
print(f"Репозиторий: {config.repository_url}")
print()
dependencies = analyzer.get_dependencies(
    package_name=config.package_name,
    version=config.package_version
)
print(analyzer.format_dependencies_output(dependencies))

graph_builder = GraphBuilder(
    analyzer=analyzer,
    max_depth=config.max_depth,
    filter_substring=config.filter_substring
)
print(f"Анализ зависимостей для пакета: {config.package_name}:{config.package_version}")
print(f"Режим: {config.repository_mode}")
print(f"Максимальная глубина: {config.max_depth}")
if config.filter_substring:
    print(f"Фильтр: '{config.filter_substring}'")
print()
graph_data = graph_builder.build_dependency_graph(
    root_package=config.package_name,
    root_version=config.package_version
)
print(graph_builder.format_graph_output(graph_data))
