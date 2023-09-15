# Developer's Guide: Publishing Private Python Packages on PyPI with Poetry

![Image](https://raw.githubusercontent.com/prasad89/blogposts/main/images/poetry-plus-cython-equals-pypi.png)

## Simplifying Package Distribution and Protecting Your Code

Sometimes, you might want to share your Python package with others but keep the source code private. To achieve this, we use Cython to hide the code before sharing the library on [PyPI](https://pypi.org), which is the official Python software repository. This way, others can use it in their projects without seeing your source code.

## Interested in Private Package Distribution?

If you're interested in publishing a proprietary package on PyPI and keeping its source code as a private asset, you're in the right place. This can be valuable when you're integrating closed-source packages as dependencies into an open-source project. In this guide, we'll explain how to use Cython for code obfuscation and how to build and publish your package using Poetry.

# Cython and Poetry

## Enhancing Code Security with Cython

[Cython](https://github.com/cython/cython) is a versatile tool known for making Python programs faster, but it can also help hide your code. It takes your Python code and turns it into C code, then compiles it into binaries. These binaries work just like regular Python modules and effectively protect your code.

## Streamlined Dependency Management with Poetry

[Poetry](https://github.com/python-poetry/poetry) managing Python dependencies simple. While it's easy to use, it may not cover every possible scenario. In some situations, you might need to use creative solutions to meet specific requirements.

## Adapting Beyond Poetry

If you're not using Poetry or prefer another approach, you can adapt the techniques we discuss here for other tools and methods. For example, you can apply these concepts with a [traditional **setup.py** file and twine](https://packaging.python.org/en/latest/tutorials/packaging-projects/#uploading-the-distribution-archives). This won't require much extra effort to achieve your goals.

# Configuring Poetry

To customize the [wheel](https://realpython.com/python-wheels) building process in Poetry, we need to override Poetry's default procedure with our custom script. To do this, you should include the following section in your **pyproject.toml** file:

```toml
[tool.poetry.build]
script = "build.py"
generate-setup-file = false
```

Usually, Poetry relies on your project's **pyproject.toml** file to automatically create a **setup.py** file behind the scenes. This **setup.py** file is then used for various tasks like "build" and "install." However, in this scenario, we're telling Poetry not to generate a **setup.py** file during package builds. Instead, we specify our custom build script named **build.py**. Poetry will invoke this script when we build our release wheel, but it won't use it during a user's package installation. In the next section, we'll explain what this script should contain and how it works.

The build script uses Cython for code compilation. To ensure that Cython is part of our Poetry development dependencies, we need to add it there. This way, only package developers need Cython, not the end-users. You can achieve this by running [**poetry add --dev Cython**](https://python-poetry.org/docs/cli/#add) or manually inserting the desired version into the [**tool.poetry.dev-dependencies**](https://python-poetry.org/docs/pyproject/#dependencies-and-dev-dependencies) section and then executing [**poetry update**](https://python-poetry.org/docs/cli/#update).

```toml
[tool.poetry.dev-dependencies]
Cython = "^3.0.0"  # Latest version at the time of publishing
```

Finally, since the main goal of this process is to protect our source code from distribution, it's crucial to ensure that the generated package doesn't contain any Python code. Poetry, by default, includes all files in the project's source directory in the package, which includes the Python files we want to keep confidential. To address this, we must explicitly configure Poetry not to include these files. To do this, we'll add an [**exclude**](https://python-poetry.org/docs/pyproject/#include-and-exclude) key in our tool.poetry section. Keep in mind that this exclusion is based on [**Path.glob**](https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob) matching, so referring to the documentation for further clarification is advisable.

Furthermore, if you've excluded **.so** files (or their Mac/Windows binary equivalents) in your project's **.gitignore** file, you'll need to [**include**](https://python-poetry.org/docs/pyproject/#include-and-exclude) them manually to your **pyproject.toml**. Poetry won't package files ignored by the project's version control system (VCS) automatically.

```toml
[tool.poetry]
# ...
exclude = ["SRC/**/*.py"]  # Replace SRC with the root of your source
include = ["SRC/**/*.so"]  # And/or Windows/Mac equivalents
```

# Understanding the build.py Script: Building Your Project

Let's dive into the heart of our project-building process—the **build.py** script. Don't worry; it's not as complicated as it might sound. In reality, it handles a few simple tasks:

1. **Gathering Python Files:** It collects all the Python files from your project.
2. **Cython Conversion:** It transforms these Python files into binary blobs using Cython.
3. **Integration with Poetry:** It puts these resulting binaries back into your source tree, which Poetry will later incorporate.

First, let's set things up. You'll need to adjust the **SOURCE_DIR** variable to match your project structure.

```python
import multiprocessing
from pathlib import Path
from typing import List

from setuptools import Extension, Distribution

from Cython.Build import cythonize
from Cython.Distutils.build_ext import new_build_ext as cython_build_ext

SOURCE_DIR = Path("SRC")  # Replace "SRC" with your project's root
BUILD_DIR = Path("BUILD")
```

Next, we'll create a function that identifies all Python files and builds them as [Distutils/Setuptools **Extension**](https://docs.python.org/3/distutils/setupscript.html#describing-extension-modules) objects, which are standard for Python build scripts, including Cython.

```python
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
```

Now, let's create a function that takes these **Extension** objects and performs the Cython compilation using Cython's [**cythonize**](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#cythonize-arguments) function with some configurations.

```python
def cythonize_helper(extension_modules: List[Extension]) -> List[Extension]:
    return cythonize(
        module_list=extension_modules,
        build_dir=BUILD_DIR,  # Avoid building in the source tree
        annotate=False,  # No need to generate an .html output file
        nthreads=multiprocessing.cpu_count() * 2,  # Parallelize the build
        compiler_directives={"language_level": "3", "annotation_typing": False},  # Indicate Python 3 usage to Cython without using type hints annotations
        force=True,  # (Optional) Always rebuild, even if files are untouched
    )
```

Finally, we'll put everything together. We'll utilize the Setuptools **Distribution** object to handle the build orchestration. This is similar to how a [standard **setup.py**](https://docs.python.org/3/distutils/extending.html) file would execute [for building Cython code](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#basic-setup-py).

```python
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
```

# Creating the Wheel Package

Congratulations, you're almost there! To build a **.whl** package for your project, simply run [**poetry build --format wheel**](https://python-poetry.org/docs/cli/#build).

Once the process is complete, you can [open the resulting **.whl** file using a **.zip** extractor](https://stackoverflow.com/questions/32923952/how-do-i-list-the-files-inside-a-python-wheel). Inside, you'll discover binary versions of all your Python files.

Please ensure that you do not distribute an sdist package, as it contains uncompiled source code. We specify **--format wheel** to exclusively build the wheel package, eliminating any risk of accidental PyPI publication. If you want more details during the build process, you can use the **-vvv** flag, which provides information about the files being built and added to the **.whl** package.

# Publishing Your Package to PyPI

Now that we have our wheel file ready, it's time to share it on PyPI. Fortunately, this is a common task when using Poetry, and it fits smoothly into our workflow. Many online tutorials are available to guide you through this process, like [this one](https://johnfraney.ca/blog/create-publish-python-package-poetry/#publishing-the-package). They all rely on the [**poetry publish**](https://python-poetry.org/docs/cli/#publish) command.

# Final Thoughts

One thing to keep in mind about our wheel files is that you'll need to create one for each Python version and platform (OS + architecture) you want to support. These files contain pre-compiled code, so they're not as flexible as Python source code, which can run on different systems. This practice is common among projects on PyPI, like [TensorFlow](https://pypi.org/project/tensorflow/#files).

To simplify the process of generating these wheels for your target platforms, you can use [CI/CD build matrices](https://docs.github.com/en/actions/using-workflows/about-workflows#using-a-build-matrix).

If you ever run into any confusion or issues while following this tutorial, feel free to open an issue if you need assistance. I'm here to help. While you're there, you can also check out some of my other public repositories.

— **prasad89** [(GitHub)](https://github.com/prasad89)
