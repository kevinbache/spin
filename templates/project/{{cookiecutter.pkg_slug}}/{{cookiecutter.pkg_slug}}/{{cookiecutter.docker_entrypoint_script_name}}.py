from {{ cookiecutter.pkg_slug }} import settings
import inspect


def main_funk():
    package_root = settings.PACKAGE_ROOT_PATH
    package_name = str(package_root).replace(str(package_root.parents[0]), '')[1:]
    this_file = __file__
    function_name = inspect.stack()[0][3]

    print(f"""
        Package:            {package_name}
        Rooted at:          {package_root}
        Running in file:    {this_file}
        Inside function:    {function_name}
    """)
