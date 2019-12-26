from setuptools import setup


def main():
    setup(
        name='nameko-injector',
        description='Injector support in nameko',
        # long_description=long_description + '\n\n' + history_txt,
        version='0.1.0',
        # url='https://github.com/tox-dev/tox-pipenv',
        license='MIT',
        platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
        author='Volodymyr Vitvitskyi',
        # classifiers=['Development Status :: 4 - Beta',
        #              'Intended Audience :: Developers',
        #              'License :: OSI Approved :: MIT License',
        #              'Operating System :: POSIX',
        #              'Operating System :: Microsoft :: Windows',
        #              'Operating System :: MacOS :: MacOS X',
        #              'Topic :: Software Development :: Testing',
        #              'Topic :: Software Development :: Libraries',
        #              'Topic :: Utilities',
        #              'Programming Language :: Python',
        #              ],
        packages=['nameko_injector', ],
        py_modules=['nameko_injector'],
        install_requires=['nameko>=2.0.0', 'injector>=0.18.0'],
        # entry_points={'tox': ['pipenv = tox_pipenv.plugin']},
        # tests_require=['pytest','pytest-mock']
    )


if __name__ == '__main__':
    main()
