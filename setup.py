from setuptools import setup, find_packages

setup(
    name="folder_sync_pro",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        'pillow>=11.1.0',
        'watchdog>=6.0.0',
        'pywin32>=310; sys_platform == "win32"'
    ],
)