import multiprocessing
from pathlib import Path
from typing import List

from setuptools import Extension, Distribution

from Cython.Build import cythonize
from Cython.Distutils.build_ext import new_build_ext as cython_build_ext

SOURCE_DIR = Path("SRC")  # Replace "SRC" with your project's root
BUILD_DIR = Path("BUILD")


def build() -> None:
    extension_modules = cythonize_helper(get_extension_modules())

    # Use Setuptools to collect files
    distribution = Distribution({
        "ext_modules": extension_modules,
        "cmdclass": {
            "build_ext": cython_build_ext,
        },
    })

    # Copy all files back to the source directory
    # This ensures that Poetry can include them in its build
    build_ext_cmd = distribution.get_command_obj("build_ext")
    build_ext_cmd.ensure_finalized()
    build_ext_cmd.inplace = 1
    build_ext_cmd.run()


def get_extension_modules() -> List[Extension]:
    extension_modules: List[Extension] = []

    for py_file in SOURCE_DIR.rglob("*.py"):
        module_path = py_file.with_suffix("")

        module_path = str(module_path).replace("/", ".")

        extension_module = Extension(
            name=module_path,
            sources=[str(py_file)]
        )

        extension_modules.append(extension_module)

    return extension_modules


def cythonize_helper(extension_modules: List[Extension]) -> List[Extension]:
    return cythonize(
        module_list=extension_modules,
        build_dir=BUILD_DIR,  # Avoid building in the source tree
        annotate=False,  # No need to generate a .html output file
        nthreads=multiprocessing.cpu_count()*2,  # Parallelize the build
        compiler_directives={"language_level": "3",
                             "annotation_typing": False},  # Indicate Python 3 usage to Cython without using type hints annotations
        force=True,  # (Optional) Always rebuild, even if files are untouched
    )


if __name__ == "__main__":
    build()
