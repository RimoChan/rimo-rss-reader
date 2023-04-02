import setuptools


setuptools.setup(
    name='rimo_rss_reader',
    version='1.1.1',
    author='RimoChan',
    author_email='the@librian.net',
    description='librian',
    long_description=open('readme.md', encoding='utf8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/RimoChan/rimo-rss-reader',
    packages=[
        'rimo_rss_reader',
    ],
    package_data={
        'rimo_rss_reader': ['web/*']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    install_requires=open('requirements.txt', encoding='utf8').read().splitlines(),
    python_requires='>=3.8',
)
