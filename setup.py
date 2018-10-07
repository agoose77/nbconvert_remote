from setuptools import setup, find_packages
setup(
    name="nbconvert_http",
    version="0.1",
    packages=find_packages(),

    install_requires=['nbconvert', 'quart', 'rfc6266', 'traitlets', 'nbformat'],

    package_data={
        '': ['*.txt', '*.rst'],
    },

    # metadata to display on PyPI
    author="Angus Hollands",
    author_email="goosey15@gmail.com",
    description="HTTP frontend to nbconvert. Currently doesn't execute the notebook.",
    license="MIT",
    keywords="http nbconvert",
    url="https://github.com/agoose77/nbconvert_remote",
    entry_points={
        'console_scripts': [
            'nbconvert-http=nbconvert_http.serve:main'
        ]
    }
)