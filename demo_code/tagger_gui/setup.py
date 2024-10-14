from setuptools import setup

setup(
    name='tagger_gui',  # Replace with your package name
    version='0.1',   # Version of your package
    packages=['tagger_gui'],  # Automatically find packages in your project
    install_requires=[
        'requests>=2.32.3',
        'rdflib>=7.0.0',
        'flask>=3.0.3',
        'flask_cors>=5.0.0',
    ],
    author='MAST',
    author_email='alucy@stsci.edu',
    description='Just a test.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    python_requires='>=3.0',  # Specify the minimum Python version
    entry_points={
        'console_scripts': [
            'tagger=tagger_gui.tagger_app_tk:main',  # Points to the main function
        ],
    },
)