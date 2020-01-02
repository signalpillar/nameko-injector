from pathlib import Path
from setuptools import setup


def main():
    setup(
        name="nameko-injector",
        description="Injector support in nameko",
        long_description=Path("README.md").read_text(),
        version="0.1.0",
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
        packages=["nameko_injector",],
        py_modules=["nameko_injector"],
        install_requires=["nameko>=2.0.0", "injector>=0.18.0"],
    )


if __name__ == "__main__":
    main()
