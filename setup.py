try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '0.1.0'

# long description
with open('README.md') as readme_file:
    readme = readme_file.read()


setup(
    name='dqueue',
    packages=['dqueue'],
    version=version,
    author='Vitaly R. Samigullin',
    author_email='vrs@pilosus.org',
    description='Distributed queue based on Redis',
    long_description=readme,
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        'Programming Language :: Python :: 3.6',
        'Topic :: Database'
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'redis',
    ],
)
