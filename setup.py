from setuptools import setup, find_packages

VERSION = 0.1

setup(
    name='bitrix24-bridge-oscar',
    version=VERSION,
    url='https://github.com/initflow/bitrix24-bridge-oscar',
    author="Aidar Rakhimov",
    author_email="rakhimov.aidar@initflow.com",
    description="Sync bridge with Bitrix24 via bitrix24-bridge",
    long_description=open('README.md').read(),
    license=open('LICENSE').read(),
    platforms=['linux', 'mac'],
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    test_suite="tests",
    install_requires=[
        'requests>=1.0',
        'django-oscar>=2.0',
    ],
    # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Other/Nonlisted Topic',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)