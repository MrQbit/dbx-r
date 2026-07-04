from setuptools import setup, find_packages
setup(
    name="duet_tasks",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["psutil"],
    python_requires=">=3.10",
)
