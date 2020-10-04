from pathlib import Path

from setuptools import find_packages, setup


def main():
    setup(
        name="nameko-injector",
        description="Injector support in nameko",
        long_description=Path("README.rst").read_text(),
        version="1.1.1",
        url="https://github.com/signalpillar/nameko-injector",
        license="MIT",
        platforms=["linux", "osx"],
        author="Volodymyr Vitvitskyi",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: MacOS :: MacOS X",
            "Topic :: Software Development :: Testing",
            "Topic :: Software Development :: Libraries",
            "Topic :: Utilities",
            "Programming Language :: Python",
        ],
        packages=find_packages(),
        py_modules=["nameko_injector"],
        install_requires=["nameko>=2.0.0", "injector>=0.18.0"],
    )


if __name__ == "__main__":
    main()
